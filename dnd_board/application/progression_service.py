from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace

from dnd_board.application.character_state_service import (
    CharacterStatePersistence,
    clear_active_concentration,
)
from dnd_board.application.room_state import Room
from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    CharacterClassLevel,
    CharacterSheet,
    ClassType,
    PartyMemberConfig,
    PartyMemberSheet,
    SpellEntry,
    SpellSource,
    ability_modifier,
    enum_key,
    enum_label,
    enum_value,
)
from dnd_board.rules.progression import (
    AbilityScoreChoiceDefinition,
    CLASS_PROGRESSION_DEFINITIONS,
    FeatGrant,
    FeatChoiceDefinition,
    HitPointChoiceOption,
    HitPointChoiceDefinition,
    HitPointGrant,
    ProgressionChoiceId,
    ProgressionGrantRecord,
    ProgressionRuleViolation,
    SpellCollection,
    SpellChoiceDefinition,
    SpellGrant,
    SpellGrantScope,
    SpellLevelCategory,
    SpellPool,
    SPELL_PROGRESSION_DEFINITIONS,
    SubclassChoiceDefinition,
    SubclassGrant,
    SkillSelectionIssue,
    apply_progression_grants,
    apply_class_option_progression_grants,
    apply_fighting_style_progression_grants,
    apply_ability_score_progression_grants,
    apply_subclass_progression_grants,
    active_spell_progression_entries,
    class_hit_die,
    level_advance_allowed,
    prune_progression_choices,
    evaluate_progression_rule,
    progression_rule,
    reconcile_progression_grant_records,
    update_class_level,
    spell_grant_scopes,
    spell_choice_level_category,
    spell_choice_candidates,
    progression_requirements_met,
    replace_progression_grant_record,
    spell_entries_for_collection,
    subclass_grant_classes,
    subclass_matches_class,
    progression_feat_grants,
)
from dnd_board.rules.feats import selected_general_feat_types, selected_fighting_styles


MemberUpdate = Callable[[PartyMemberConfig], None]


@dataclass(frozen=True)
class ProgressionOperations:
    update_member: Callable[[str, str, MemberUpdate], PartyMemberConfig | None]
    state_persistence: CharacterStatePersistence


class ProgressionServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def level_character(
    room: Room,
    sheet: CharacterSheet,
    class_type: ClassType,
    delta: int,
    operations: ProgressionOperations,
) -> PartyMemberConfig:
    level_delta = max(-1, min(1, delta))
    if level_delta > 0 and not level_advance_allowed(sheet.pendingChoices):
        raise ProgressionServiceError(
            status_code=400,
            detail=(
                "Resolve pending level choices before leveling up: "
                f"{pending_choice_summary(sheet)}"
            ),
        )

    updated_member = operations.update_member(
        room.id,
        sheet.id,
        lambda member: set_member_class_levels(
            member,
            update_class_level(
                member_sheet_classes(member),
                class_type,
                level_delta,
            ),
        ),
    )
    if updated_member is None:
        raise ProgressionServiceError(status_code=404, detail="Sheet not found")

    clear_progression_runtime_state(room, updated_member.id, operations)
    return updated_member


def apply_progression_selection(
    room: Room,
    sheet_id: str,
    choice_id: ProgressionChoiceId,
    values: list[str],
    operations: ProgressionOperations,
) -> PartyMemberConfig:
    updater = progression_choice_updater(choice_id, values)
    updated_member = operations.update_member(room.id, sheet_id, updater)
    if updated_member is None:
        raise ProgressionServiceError(status_code=404, detail="Sheet not found")
    room.resource_uses.pop(updated_member.id, None)
    return updated_member


def progression_choice_updater(
    choice_id: ProgressionChoiceId,
    values: list[str],
) -> MemberUpdate:
    return lambda member: apply_member_progression_rule(member, choice_id, values)


def clear_progression_runtime_state(
    room: Room,
    member_id: str,
    operations: ProgressionOperations,
) -> None:
    room.resource_uses.pop(member_id, None)
    room.hit_points.pop(member_id, None)
    room.temporary_hit_points.pop(member_id, None)
    room.max_hit_point_increases.pop(member_id, None)
    room.max_hit_point_reductions.pop(member_id, None)
    room.exhaustion_levels.pop(member_id, None)
    room.condition_overrides.pop(member_id, None)
    room.condition_durations.pop(member_id, None)
    room.condition_removals.pop(member_id, None)
    clear_active_concentration(room, member_id, operations.state_persistence)
    room.damage_resistances.pop(member_id, None)
    room.damage_vulnerabilities.pop(member_id, None)
    room.damage_immunities.pop(member_id, None)


def member_sheet_classes(member: PartyMemberConfig) -> list[CharacterClassLevel]:
    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)])
    if not member.sheet.classes:
        member.sheet.classes = [CharacterClassLevel(name=ClassType.FIGHTER, level=1)]
    return prune_progression_choices(member.sheet.classes)


def set_member_class_levels(member: PartyMemberConfig, classes: list[CharacterClassLevel]) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    ensure_spell_grant_records(member)
    ensure_subclass_grant_records(member)
    ensure_progression_base_hit_points(member)
    member.sheet.classes = prune_progression_choices(classes)
    member.sheet.progressionGrants = subclass_grants_matching_classes(
        member.sheet.progressionGrants or [],
        member.sheet.classes,
    ) or None
    reconcile_member_progression_grants(member)


def pending_choice_summary(sheet: CharacterSheet) -> str:
    return ", ".join(choice.label for choice in sheet.pendingChoices)


def apply_member_progression_rule(
    member: PartyMemberConfig,
    choice_id: ProgressionChoiceId,
    values: list[str],
) -> None:
    classes = member_sheet_classes(member)
    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=classes)
    ensure_spell_grant_records(member)
    ensure_subclass_grant_records(member)
    ensure_progression_base_skills(member)
    ensure_progression_base_ability_scores(member)
    ensure_progression_base_hit_points(member)
    skills = dict(member.sheet.skills or {})
    rule = progression_rule(
        choice_id,
        classes,
        skills,
        member.sheet.progressionGrants,
    )
    if rule is None:
        raise ProgressionServiceError(status_code=400, detail="Unsupported progression rule")
    try:
        choice = rule.choices[0] if len(rule.choices) == 1 else None
        hit_point_option = (
            enum_value(HitPointChoiceOption, values[0])
            if isinstance(choice, HitPointChoiceDefinition) and values
            else None
        )
        hit_die_result = (
            random.randint(1, choice.hitDie)
            if isinstance(choice, HitPointChoiceDefinition)
            and hit_point_option == HitPointChoiceOption.ROLL
            else None
        )
        evaluation = evaluate_progression_rule(
            rule,
            classes,
            skills,
            values,
            spellbook=member.sheet.spellbook,
            constitution_modifier=member_constitution_modifier(member),
            hit_point_bonus=member_hit_point_bonus(member),
            hit_die_result=hit_die_result,
            ability_scores=member.abilityScores,
            selected_feats=tuple(selected_general_feat_types(member.sheet.feats)),
            selected_fighting_styles=tuple(selected_fighting_styles(classes)),
            feat_eligibility_sheet=member_feat_eligibility_sheet(member),
        )
    except ProgressionRuleViolation as error:
        raise ProgressionServiceError(
            status_code=400,
            detail=progression_rule_error(rule, error.issue),
        ) from error

    previous_records = list(member.sheet.progressionGrants or [])
    records, previous_record = replace_progression_grant_record(
        previous_records,
        evaluation,
    )
    replaced_spell_scopes = spell_grant_scopes([previous_record] if previous_record else [])
    managed_subclass_classes = subclass_grant_classes(
        [record for record in [previous_record] if record is not None]
    ) | subclass_grant_classes([ProgressionGrantRecord(evaluation.source, evaluation.grants)])
    if managed_subclass_classes:
        replaced_spell_scopes.update(spell_grant_scopes(previous_records))
        member.sheet.classes = apply_subclass_progression_grants(
            classes,
            records,
            managed_subclass_classes,
        )
        classes = member.sheet.classes
    replaced_spell_scopes.update(spell_grant_scopes([
        ProgressionGrantRecord(evaluation.source, evaluation.grants),
    ]))
    if any(scope.destination == SpellCollection.SPELLBOOK for scope in replaced_spell_scopes):
        for record in records:
            dependent_rule = progression_rule(record.source.rule, classes, skills)
            if (
                dependent_rule is not None
                and len(dependent_rule.choices) == 1
                and isinstance(dependent_rule.choices[0], SpellChoiceDefinition)
                and dependent_rule.choices[0].pool == SpellPool.CHARACTER_COLLECTION
                and dependent_rule.choices[0].poolCollection == SpellCollection.SPELLBOOK
            ):
                replaced_spell_scopes.update(spell_grant_scopes([record]))
    records = reconcile_progression_grant_records(
        member.sheet.baseSkills,
        records,
        classes,
    )
    member.sheet.progressionGrants = records
    apply_member_ability_score_grants(member, records)
    apply_member_feat_grants(member, previous_records, records)
    derive_member_max_hit_points(member, records, classes)
    member.sheet.classes = apply_fighting_style_progression_grants(
        member.sheet.classes or [],
        previous_records,
        records,
    )
    member.sheet.classes = apply_class_option_progression_grants(
        member.sheet.classes,
        previous_records,
        records,
    )
    member.sheet.skills = apply_progression_grants(member.sheet.baseSkills, records) or None
    apply_spell_progression_grants(
        member,
        records,
        replaced_scopes=replaced_spell_scopes,
    )


def reconcile_member_progression_grants(member: PartyMemberConfig) -> None:
    if member.sheet is None:
        return
    ensure_progression_base_skills(member)
    ensure_progression_base_ability_scores(member)
    if not member.sheet.progressionGrants:
        return
    previous_records = member.sheet.progressionGrants
    ensure_progression_base_hit_points(member)
    replaced_spell_scopes = spell_grant_scopes(previous_records)
    managed_subclass_classes = subclass_grant_classes(previous_records)
    classes = member.sheet.classes or []
    records = reconcile_progression_grant_records(
        member.sheet.baseSkills or {},
        member.sheet.progressionGrants,
        classes,
    )
    member.sheet.progressionGrants = records or None
    apply_member_ability_score_grants(member, records)
    apply_member_feat_grants(member, previous_records, records)
    derive_member_max_hit_points(member, records, classes)
    member.sheet.classes = apply_subclass_progression_grants(
        classes,
        records,
        managed_subclass_classes,
    )
    member.sheet.classes = apply_fighting_style_progression_grants(
        member.sheet.classes,
        previous_records,
        records,
    )
    member.sheet.classes = apply_class_option_progression_grants(
        member.sheet.classes,
        previous_records,
        records,
    )
    member.sheet.skills = apply_progression_grants(member.sheet.baseSkills or {}, records) or None
    apply_spell_progression_grants(
        member,
        records,
        replaced_scopes=replaced_spell_scopes,
    )


def ensure_progression_base_skills(member: PartyMemberConfig) -> None:
    if member.sheet is not None and member.sheet.baseSkills is None:
        member.sheet.baseSkills = dict(member.sheet.skills or {})


def ensure_progression_base_ability_scores(member: PartyMemberConfig) -> None:
    ensure_member_ability_scores(member)
    if member.baseAbilityScores is None:
        member.baseAbilityScores = AbilityScores(
            strength=member.abilityScores.strength,
            dexterity=member.abilityScores.dexterity,
            constitution=member.abilityScores.constitution,
            intelligence=member.abilityScores.intelligence,
            wisdom=member.abilityScores.wisdom,
            charisma=member.abilityScores.charisma,
        )


def apply_member_ability_score_grants(
    member: PartyMemberConfig,
    records: list[ProgressionGrantRecord],
) -> None:
    ensure_progression_base_ability_scores(member)
    next_scores = apply_ability_score_progression_grants(
        member.baseAbilityScores,
        records,
    )
    member.abilityScores = next_scores


def apply_member_feat_grants(
    member: PartyMemberConfig,
    previous_records: list[ProgressionGrantRecord],
    records: list[ProgressionGrantRecord],
) -> None:
    if member.sheet is None:
        return
    from dnd_board.rules.feats import general_feat_feature

    previous_ids = {enum_key(grant.feat) for grant in progression_feat_grants(previous_records)}
    retained = [
        feature
        for feature in member.sheet.feats or []
        if feature.id not in previous_ids
    ]
    granted = [
        feature
        for grant in progression_feat_grants(records)
        if (feature := general_feat_feature(enum_key(grant.feat))) is not None
    ]
    member.sheet.feats = [*retained, *granted] or None


def member_feat_eligibility_sheet(member: PartyMemberConfig):
    sheet = member.sheet or PartyMemberSheet()
    return SimpleNamespace(
        abilityScores=member.abilityScores,
        race=sheet.race or "",
        background=sheet.background or "",
        classes=sheet.classes or [],
        proficiencies=sheet.proficiencies or [],
        feats=sheet.feats or [],
        features=sheet.features or [],
        abilities=[],
        spells=sheet.spells or [],
    )


def ensure_subclass_grant_records(member: PartyMemberConfig) -> None:
    if member.sheet is None:
        return
    records = list(member.sheet.progressionGrants or [])
    from dnd_board.rules.progression import ProgressionGrantSource

    for character_class in member.sheet.classes or []:
        definition = CLASS_PROGRESSION_DEFINITIONS.get(character_class.name)
        choice_id = definition.subclassChoice if definition is not None else None
        if (
            choice_id is None
            or character_class.level < definition.subclassLevel
            or character_class.subclass is None
            or not subclass_matches_class(character_class.subclass, character_class.name)
            or any(record.source.rule == choice_id for record in records)
        ):
            continue
        records.append(ProgressionGrantRecord(
            source=ProgressionGrantSource(
                choice_id,
                character_class.name,
            ),
            grants=(SubclassGrant(
                characterClass=character_class.name,
                subclass=character_class.subclass,
            ),),
        ))
    member.sheet.progressionGrants = records or None


def subclass_grants_matching_classes(
    records: list[ProgressionGrantRecord],
    classes: list[CharacterClassLevel],
) -> list[ProgressionGrantRecord]:
    subclasses = {
        character_class.name: character_class.subclass
        for character_class in classes
    }
    return [
        record
        for record in records
        if all(
            not isinstance(grant, SubclassGrant)
            or subclasses.get(grant.characterClass) == grant.subclass
            for grant in record.grants
        )
    ]


def ensure_spell_grant_records(member: PartyMemberConfig) -> None:
    if member.sheet is None:
        return
    records = list(member.sheet.progressionGrants or [])
    from dnd_board.rules.progression import ProgressionGrantSource

    for choice_id in dict.fromkeys(
        definition.choice for _class_type, definition in SPELL_PROGRESSION_DEFINITIONS
    ):
        if any(record.source.rule == choice_id for record in records):
            continue
        rule = progression_rule(choice_id, member.sheet.classes or [], member.sheet.skills or {})
        if (
            rule is None
            or not progression_requirements_met(rule, member.sheet.classes or [])
            or not rule.choices
            or not all(isinstance(choice, SpellChoiceDefinition) for choice in rule.choices)
        ):
            continue
        grants: list[SpellGrant] = []
        for choice in rule.choices:
            if not isinstance(choice, SpellChoiceDefinition):
                continue
            candidates_by_id = {
                spell.id: spell
                for spell in spell_choice_candidates(
                    choice,
                    member.sheet.classes or [],
                    member.sheet.spellbook or [],
                )
            }
            existing = [
                spell
                for spell in spell_entries_for_collection(
                    choice.destination,
                    member.sheet.spells or [],
                    member.sheet.spellbook or [],
                )
                if spell.source == choice.source
                and spell.id in candidates_by_id
            ]
            grants.extend(
                SpellGrant(
                    spell=spell.id,
                    destination=choice.destination,
                    source=choice.source,
                    category=spell_choice_level_category(choice),
                    minimumClassLevel=(
                        choice.grantMinimumLevels[index]
                        if index < len(choice.grantMinimumLevels)
                        else 1
                    ),
                )
                for index, spell in enumerate(existing)
                if (
                    (spell_choice_level_category(choice) == SpellLevelCategory.CANTRIP and spell.level == 0)
                    or (spell_choice_level_category(choice) == SpellLevelCategory.LEVELED and spell.level > 0)
                )
            )
        if not grants:
            continue
        records.append(ProgressionGrantRecord(
            source=ProgressionGrantSource(
                choice_id,
                rule.requirements[0].characterClass,
                rule.requirements[0].subclass,
            ),
            grants=tuple(grants),
        ))
    member.sheet.progressionGrants = records


def apply_spell_progression_grants(
    member: PartyMemberConfig,
    records: list[ProgressionGrantRecord],
    *,
    replaced_scopes: set[SpellGrantScope],
) -> None:
    if member.sheet is None or not replaced_scopes:
        return
    for destination in (
        SpellCollection.SPELLBOOK,
        SpellCollection.KNOWN,
        SpellCollection.PREPARED,
    ):
        destination_scopes = {
            scope for scope in replaced_scopes if scope.destination == destination
        }
        if not destination_scopes:
            continue
        granted_spells = [
            spell
            for grant, spell in active_spell_progression_entries(
                records,
                member.sheet.classes or [],
                member.sheet.skills or {},
                member.sheet.spellbook or [],
                destination=destination,
            )
            if SpellGrantScope(
                grant.destination,
                grant.source,
                grant.category,
            ) in destination_scopes
        ]
        if destination == SpellCollection.SPELLBOOK:
            retained = [
                spell
                for spell in member.sheet.spellbook or []
                if not any(spell_entry_matches_grant_scope(spell, scope) for scope in destination_scopes)
            ]
            member.sheet.spellbook = [*retained, *granted_spells] or None
            continue
        retained = [
            spell
            for spell in member.sheet.spells or []
            if not any(spell_entry_matches_grant_scope(spell, scope) for scope in destination_scopes)
        ]
        member.sheet.spells = [*retained, *granted_spells] or None


def spell_entry_matches_grant_scope(
    spell: SpellEntry,
    scope: SpellGrantScope,
) -> bool:
    if spell.source != scope.source:
        return False
    if scope.category == SpellLevelCategory.CANTRIP and spell.level != 0:
        return False
    if scope.category == SpellLevelCategory.LEVELED and spell.level == 0:
        return False
    if scope.destination == SpellCollection.KNOWN:
        return True
    if scope.destination == SpellCollection.PREPARED:
        return spell.level > 0
    if scope.destination == SpellCollection.SPELLBOOK:
        return True
    return False


def progression_rule_error(rule, issue: SkillSelectionIssue) -> str:
    choice = rule.choices[0]
    if isinstance(choice, AbilityScoreChoiceDefinition):
        if issue == SkillSelectionIssue.REQUIREMENT_NOT_MET:
            return "Ability Score Improvement is not available"
        if issue == SkillSelectionIssue.WRONG_COUNT:
            return "Choose one ability twice or two abilities once"
        if issue == SkillSelectionIssue.INVALID_FEAT:
            return "Invalid feat"
        if issue == SkillSelectionIssue.INVALID_FEAT_CATEGORY:
            return "That feat is not available from this progression choice"
        if issue == SkillSelectionIssue.FEAT_ALREADY_SELECTED:
            return "Feat is already selected"
        if issue == SkillSelectionIssue.FEAT_PREREQUISITE_NOT_MET:
            return "Feat prerequisites are not met"
        return "Invalid ability score or no selected score can be increased"
    if isinstance(choice, FeatChoiceDefinition):
        if issue == SkillSelectionIssue.REQUIREMENT_NOT_MET:
            return "Feat selection is not available"
        if issue == SkillSelectionIssue.WRONG_COUNT:
            return f"Choose {choice.count} feat"
        if issue == SkillSelectionIssue.INVALID_FEAT:
            return "Invalid feat"
        if issue == SkillSelectionIssue.INVALID_FEAT_CATEGORY:
            return "That feat is not available from this progression choice"
        if issue == SkillSelectionIssue.FEAT_ALREADY_SELECTED:
            return "Feat is already selected"
        if issue == SkillSelectionIssue.FEAT_PREREQUISITE_NOT_MET:
            return "Feat prerequisites are not met"
        return "Choose a legal feat"
    if isinstance(choice, HitPointChoiceDefinition):
        if issue == SkillSelectionIssue.REQUIREMENT_NOT_MET:
            return "Hit point progression is not available"
        if issue == SkillSelectionIssue.WRONG_COUNT:
            return "Choose fixed HP or roll HP"
        return "Choose a legal hit point progression option"
    if isinstance(choice, SubclassChoiceDefinition):
        class_label = enum_key(choice.characterClass).title()
        if issue == SkillSelectionIssue.REQUIREMENT_NOT_MET:
            return f"{class_label} subclass selection is not available"
        if issue == SkillSelectionIssue.WRONG_COUNT:
            return f"Choose one {class_label} subclass"
        return f"Choose a legal {class_label} subclass"
    if isinstance(choice, SpellChoiceDefinition):
        spell_choices = tuple(
            item for item in rule.choices if isinstance(item, SpellChoiceDefinition)
        )
        source_label = enum_label(choice.source)
        if len(spell_choices) > 1:
            pool_class = next(
                (item.poolClass for item in spell_choices if item.poolClass is not None),
                None,
            )
            pool_label = enum_label(pool_class).lower() if pool_class is not None else source_label.lower()
            combined_label = f"{source_label} cantrips and {pool_label} spells"
            if issue == SkillSelectionIssue.REQUIREMENT_NOT_MET:
                return f"{combined_label} are not available"
            if issue == SkillSelectionIssue.WRONG_COUNT:
                return f"Choose {sum(item.count for item in spell_choices)} {combined_label}"
            return f"Choose legal {combined_label}"
        destination_label = {
            SpellCollection.KNOWN: f"{source_label} known spells",
            SpellCollection.SPELLBOOK: f"{source_label} spellbook spells",
            SpellCollection.PREPARED: f"prepared {source_label} spells",
        }[choice.destination]
        if issue == SkillSelectionIssue.REQUIREMENT_NOT_MET:
            return f"Complete the {source_label} spellbook before preparing spells"
        if issue == SkillSelectionIssue.WRONG_COUNT:
            return f"Choose {choice.count} {destination_label}"
        if choice.destination == SpellCollection.PREPARED:
            return f"Prepared {source_label} spells must be legal spells from your spellbook"
        return f"Choose legal {destination_label}"
    class_label = enum_key(rule.requirements[0].characterClass).title()
    is_expertise = isinstance(choice, SkillChoiceDefinition) and choice.proficiency == ProficiencyLevel.EXPERTISE
    if issue == SkillSelectionIssue.REQUIREMENT_NOT_MET:
        return f"{class_label} {'Expertise' if is_expertise else 'skill proficiencies'} are not available"
    if issue == SkillSelectionIssue.WRONG_COUNT:
        count = rule.choices[0].count
        selection_label = "Expertise skills" if is_expertise else "skill proficiencies"
        return f"Choose {count} {class_label} {selection_label}"
    if issue == SkillSelectionIssue.REQUIRES_PROFICIENCY:
        return "Expertise requires an existing skill proficiency"
    selection_label = "Expertise skill" if is_expertise else "skill proficiency"
    return f"Invalid {class_label} {selection_label}"


def member_hit_point_bonus(member: PartyMemberConfig) -> int:
    from dnd_board.rules.feats import feat_hit_point_bonus_per_level
    from dnd_board.rules.species import SpeciesType, species_definition

    feat_bonus = feat_hit_point_bonus_per_level(member.sheet.feats if member.sheet else [])
    species = (
        enum_value(SpeciesType, member.sheet.race)
        if member.sheet is not None and member.sheet.race
        else None
    )
    species_bonus = species_definition(species).hitPointBonusPerLevel if species is not None else 0
    return feat_bonus + species_bonus


def class_level_one_hit_points(class_name: ClassType) -> int:
    return class_hit_die(class_name)


def member_constitution_modifier(member: PartyMemberConfig) -> int:
    constitution = member.abilityScores.constitution if member.abilityScores else 10
    return ability_modifier(constitution)


def ensure_progression_base_hit_points(member: PartyMemberConfig) -> None:
    if member.baseMaxHp is not None:
        return
    classes = member.sheet.classes if member.sheet and member.sheet.classes else []
    records = member.sheet.progressionGrants if member.sheet else []
    primary_class = classes[0].name if classes else ClassType.FIGHTER
    member.baseMaxHp = class_level_one_hit_points(primary_class)
    if member.maxHp is None:
        return
    member.manualMaxHpAdjustment = member.maxHp - calculated_member_max_hit_points(
        member,
        records or [],
        classes,
        manual_adjustment=0,
    )


def derive_member_max_hit_points(
    member: PartyMemberConfig,
    records: list[ProgressionGrantRecord],
    classes: list[CharacterClassLevel],
) -> None:
    ensure_progression_base_hit_points(member)
    member.maxHp = calculated_member_max_hit_points(
        member,
        records,
        classes,
        manual_adjustment=member.manualMaxHpAdjustment,
    )


def calculated_member_max_hit_points(
    member: PartyMemberConfig,
    records: list[ProgressionGrantRecord],
    classes: list[CharacterClassLevel],
    *,
    manual_adjustment: int,
) -> int:
    from dnd_board.rules.feats import feat_static_hit_point_bonus

    per_level_bonus = member_constitution_modifier(member) + member_hit_point_bonus(member)
    first_level_hit_points = max(1, (member.baseMaxHp or 0) + per_level_bonus)
    level_increases = sum(
        max(
            1,
            grant.hitDieResult + per_level_bonus,
        )
        for record in records
        for grant in record.grants
        if isinstance(grant, HitPointGrant)
    )
    static_bonus = feat_static_hit_point_bonus(member.sheet.feats if member.sheet else [])
    return max(1, first_level_hit_points + level_increases + static_bonus + manual_adjustment)


def ensure_member_ability_scores(member: PartyMemberConfig) -> None:
    if member.abilityScores is None:
        member.abilityScores = AbilityScores(strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10)


def unique_clean_values(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        clean_value = value.strip()
        if clean_value and clean_value not in cleaned:
            cleaned.append(clean_value)
    return cleaned


def normalize_choice_id(value: str) -> str:
    return value.strip().replace("-", "").replace("_", "").lower()
