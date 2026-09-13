import { useEffect, useMemo, useState } from "react";
import type {
  AbilityScores,
  AbilityType,
  CharacterBuilderDraft,
  CharacterBuilderOptions,
  CharacterSheet
} from "../types";
import { ABILITY_SCORE_OPTIONS } from "../character/abilityOptions";

const ABILITY_SCORE_METHOD_STANDARD_ARRAY = "standardArray";
const ABILITY_SCORE_METHOD_POINT_BUY = "pointBuy";
const ABILITY_SCORE_METHOD_RANDOM = "random";

export function CharacterBuilderPanel({
  isDm,
  onCreateCharacter,
  playerKey,
  roomId,
  sheets
}: {
  isDm: boolean;
  onCreateCharacter: (draft: CharacterBuilderDraft) => Promise<void>;
  playerKey: string;
  roomId: string;
  sheets: CharacterSheet[];
}) {
  const [options, setOptions] = useState<CharacterBuilderOptions | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const memberOptions = useMemo(() => characterBuilderMemberOptions(isDm, playerKey, sheets), [isDm, playerKey, sheets]);
  const [draft, setDraft] = useState<CharacterBuilderDraft>(() => defaultCharacterBuilderDraft(memberOptions[0]?.value ?? playerKey));
  const classDetail = options?.classDetails[draft.className];
  const backgroundDetail = options?.backgroundDetails[draft.background];
  const selectedToolDetail = draft.toolProficiency ? options?.toolDetails[draft.toolProficiency] : undefined;
  const magicInitiateChoices = backgroundDetail?.magicInitiateSpellChoices;
  const usesScorePool = draft.abilityScoreMethod !== ABILITY_SCORE_METHOD_POINT_BUY;
  const scorePool = draft.abilityScoreMethod === ABILITY_SCORE_METHOD_RANDOM ? draft.rolledAbilityScores : options?.standardArray ?? [];
  const availableScoreCounts = countScoreValues(scorePool);
  const pointBuySpent = ABILITY_SCORE_OPTIONS.reduce((sum, ability) => sum + (options?.pointBuyCosts[String(draft.baseAbilityScores[ability.value])] ?? 0), 0);
  const backgroundIncreaseMode = Object.values(draft.backgroundAbilityIncreases).filter((increase) => increase > 0).length === 3 ? "oneEach" : "twoOne";
  const backgroundPlusTwo = ABILITY_SCORE_OPTIONS.find((ability) => draft.backgroundAbilityIncreases[ability.value] === 2)?.value ?? (backgroundDetail?.abilityScores[0]?.value as AbilityType | undefined);
  const backgroundPlusOne = ABILITY_SCORE_OPTIONS.find((ability) => draft.backgroundAbilityIncreases[ability.value] === 1)?.value ?? (backgroundDetail?.abilityScores[1]?.value as AbilityType | undefined);

  useEffect(() => {
    let active = true;
    fetch(`/api/rooms/${encodeURIComponent(roomId)}/character-builder/options`)
      .then((response) => response.json())
      .then((body: CharacterBuilderOptions) => {
        if (active) {
          setOptions(body);
          setDraft((current) => normalizeCharacterBuilderDraft(current, body));
        }
      })
      .catch((error) => console.error(error));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setDraft((current) => {
      const fallbackMemberId = memberOptions[0]?.value ?? playerKey;
      const memberId = isDm && memberOptions.some((option) => option.value === current.memberId) ? current.memberId : fallbackMemberId;
      return { ...current, memberId };
    });
  }, [isDm, memberOptions, playerKey]);

  const updateDraft = (patch: Partial<CharacterBuilderDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const updateBaseAbilityScore = (ability: AbilityType, value: number) => {
    setDraft((current) => ({
      ...current,
      baseAbilityScores: updatedBaseAbilityScores(current, ability, value)
    }));
  };
  const updateBackground = (background: string) => {
    if (!options) {
      updateDraft({ background });
      return;
    }
    setDraft((current) => normalizeCharacterBuilderDraft({ ...current, background }, options));
  };
  const updateClass = (className: string) => {
    if (!options) {
      updateDraft({ className });
      return;
    }
    setDraft((current) => normalizeCharacterBuilderDraft({ ...current, className }, options));
  };
  const updateStringList = (field: keyof Pick<CharacterBuilderDraft, "classSkillProficiencies" | "classExpertise" | "wizardCantrips" | "wizardSpellbookSpells" | "wizardPreparedSpells">, index: number, value: string) => {
    if (!options) return;
    setDraft((current) => {
      const next = [...current[field]];
      next[index] = value;
      return normalizeCharacterBuilderDraft({ ...current, [field]: next }, options);
    });
  };
  const updateIncreaseMode = (mode: "twoOne" | "oneEach") => {
    if (!backgroundDetail) return;
    const abilities = backgroundDetail.abilityScores.map((option) => option.value as AbilityType);
    updateDraft({ backgroundAbilityIncreases: abilityIncreasesForMode(mode, abilities) });
  };
  const updateTwoOneIncrease = (amount: 1 | 2, ability: AbilityType) => {
    if (!backgroundDetail) return;
    const abilities = backgroundDetail.abilityScores.map((option) => option.value as AbilityType);
    const otherAmount = amount === 2 ? 1 : 2;
    const otherAbility = ABILITY_SCORE_OPTIONS.find((option) => draft.backgroundAbilityIncreases[option.value] === otherAmount)?.value;
    updateDraft({ backgroundAbilityIncreases: abilityIncreasesForTwoOne(abilities, amount === 2 ? ability : otherAbility, amount === 1 ? ability : otherAbility) });
  };

  const updateMagicInitiateSpell = (index: number, spellId: string) => {
    const nextSpells = [...draft.magicInitiateSpells];
    nextSpells[index] = spellId;
    updateDraft({ magicInitiateSpells: nextSpells });
  };
  const updateAbilityScoreMethod = (abilityScoreMethod: string) => {
    if (!options) {
      updateDraft({ abilityScoreMethod });
      return;
    }
    const rolledAbilityScores = abilityScoreMethod === ABILITY_SCORE_METHOD_RANDOM && draft.rolledAbilityScores.length !== 6 ? rollAbilityScorePool() : draft.rolledAbilityScores;
    setDraft((current) => ({
      ...current,
      abilityScoreMethod,
      rolledAbilityScores,
      baseAbilityScores: baseAbilityScoresForMethod(abilityScoreMethod, options, rolledAbilityScores)
    }));
  };
  const rerollAbilityScores = () => {
    if (!options) return;
    const rolledAbilityScores = rollAbilityScorePool();
    updateDraft({
      abilityScoreMethod: ABILITY_SCORE_METHOD_RANDOM,
      rolledAbilityScores,
      baseAbilityScores: baseAbilityScoresForMethod(ABILITY_SCORE_METHOD_RANDOM, options, rolledAbilityScores)
    });
  };
  const characterBuilderInvalid = draft.abilityScoreMethod === ABILITY_SCORE_METHOD_POINT_BUY && pointBuySpent > (options?.pointBuyPoints ?? 0);

  const create = async () => {
    setSaving(true);
    try {
      await onCreateCharacter(draft);
      setOpen(false);
    } finally {
      setSaving(false);
    }
  };

  if (!options) return null;
  if (memberOptions.length === 0) return null;

  return (
    <section className="sheet-panel character-builder-panel">
      <div className="panel-title-row">
        <h2>Character Builder</h2>
        <button type="button" onClick={() => setOpen((current) => !current)}>
          {open ? "Close" : "Build"}
        </button>
      </div>
      {open && (
        <div className="character-builder-grid">
          <label>
            Slot
            <select value={draft.memberId} disabled={!isDm} onChange={(event) => updateDraft({ memberId: event.currentTarget.value })}>
              {memberOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Name
            <input value={draft.name} onChange={(event) => updateDraft({ name: event.currentTarget.value })} />
          </label>
          <label>
            Class
            <select value={draft.className} onChange={(event) => updateClass(event.currentTarget.value)}>
              {options.classes.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Race
            <select value={draft.race} onChange={(event) => updateDraft({ race: event.currentTarget.value })}>
              {options.races.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Background
            <select value={draft.background} onChange={(event) => updateBackground(event.currentTarget.value)}>
              {options.backgrounds.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scores
            <select value={draft.abilityScoreMethod} onChange={(event) => updateAbilityScoreMethod(event.currentTarget.value)}>
              {options.abilityScoreMethods.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Tool
            <select value={draft.toolProficiency ?? ""} onChange={(event) => updateDraft({ toolProficiency: event.currentTarget.value })}>
              {(backgroundDetail?.toolOptions ?? []).length === 0 && <option value="">None</option>}
              {(backgroundDetail?.toolOptions ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {selectedToolDetail && (
            <div className="builder-detail-list">
              <span>{selectedToolDetail.category} · {abilityLabel(selectedToolDetail.ability)} · {selectedToolDetail.cost}{selectedToolDetail.weightLb != null ? ` · ${selectedToolDetail.weightLb} lb.` : ""}</span>
              {selectedToolDetail.utilizeActions.length > 0 && <small>Utilize: {selectedToolDetail.utilizeActions.map((action) => `${action.description} DC ${action.dc}`).join("; ")}</small>}
              {selectedToolDetail.craftOutputs.length > 0 && <small>Craft: {selectedToolDetail.craftOutputs.join(", ")}</small>}
            </div>
          )}
          <label>
            Equipment
            <select value={draft.equipmentChoice} onChange={(event) => updateDraft({ equipmentChoice: event.currentTarget.value })}>
              {(backgroundDetail?.equipmentChoices ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {magicInitiateChoices && (
            <div className="builder-spell-choices">
              <div className="builder-subsection-title">Magic Initiate ({magicInitiateChoices.spellList})</div>
              {Array.from({ length: magicInitiateChoices.cantripsKnown }).map((_, index) => (
                <label key={`magic-initiate-cantrip-${index}`}>
                  Cantrip {index + 1}
                  <select value={draft.magicInitiateSpells[index] ?? ""} onChange={(event) => updateMagicInitiateSpell(index, event.currentTarget.value)}>
                    {magicInitiateChoices.cantrips.map((option) => (
                      <option key={option.value} value={option.value} disabled={draft.magicInitiateSpells.includes(option.value) && draft.magicInitiateSpells[index] !== option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              {Array.from({ length: magicInitiateChoices.firstLevelSpellsKnown }).map((_, index) => {
                const spellIndex = magicInitiateChoices.cantripsKnown + index;
                return (
                  <label key={`magic-initiate-first-${index}`}>
                    1st-Level Spell
                    <select value={draft.magicInitiateSpells[spellIndex] ?? ""} onChange={(event) => updateMagicInitiateSpell(spellIndex, event.currentTarget.value)}>
                      {magicInitiateChoices.firstLevelSpells.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                );
              })}
              <div className="builder-detail-list">
                {draft.magicInitiateSpells.map((spellId) => selectedMagicInitiateSpellOption(magicInitiateChoices, spellId)).filter(Boolean).map((spell) => (
                  <small key={spell!.value}>{spell!.label}: {spell!.level === 0 ? "Cantrip" : `Level ${spell!.level}`} · {spell!.range} · {spell!.duration} · {spell!.components.join(", ") || "None"}</small>
                ))}
              </div>
            </div>
          )}
          {classDetail && classDetail.skillProficiencies.maximum > 0 && (
            <div className="builder-spell-choices">
              <div className="builder-subsection-title">Class Skills</div>
              {Array.from({ length: classDetail.skillProficiencies.maximum }).map((_, index) => (
                <label key={`class-skill-${index}`}>
                  Skill {index + 1}
                  <select value={draft.classSkillProficiencies[index] ?? ""} onChange={(event) => updateStringList("classSkillProficiencies", index, event.currentTarget.value)}>
                    {(classDetail.skillProficiencies.options ?? []).map((option) => (
                      <option key={option.value} value={option.value} disabled={draft.classSkillProficiencies.includes(option.value) && draft.classSkillProficiencies[index] !== option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          )}
          {classDetail && classDetail.fightingStyles.maximum > 0 && (
            <label>
              Fighting Style
              <select value={draft.fightingStyle} onChange={(event) => updateDraft({ fightingStyle: event.currentTarget.value })}>
                {(classDetail.fightingStyles.options ?? []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          {classDetail && classDetail.expertise.maximum > 0 && (
            <div className="builder-spell-choices">
              <div className="builder-subsection-title">Expertise</div>
              {Array.from({ length: classDetail.expertise.maximum }).map((_, index) => (
                <label key={`class-expertise-${index}`}>
                  Skill {index + 1}
                  <select value={draft.classExpertise[index] ?? ""} onChange={(event) => updateStringList("classExpertise", index, event.currentTarget.value)}>
                    {expertiseOptions(draft, classDetail, backgroundDetail).map((option) => (
                      <option key={option.value} value={option.value} disabled={draft.classExpertise.includes(option.value) && draft.classExpertise[index] !== option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          )}
          {classDetail && classDetail.wizardSpells.cantripsKnown > 0 && (
            <div className="builder-spell-choices">
              <div className="builder-subsection-title">Wizard Spells</div>
              {Array.from({ length: classDetail.wizardSpells.cantripsKnown }).map((_, index) => (
                <label key={`wizard-cantrip-${index}`}>
                  Cantrip {index + 1}
                  <select value={draft.wizardCantrips[index] ?? ""} onChange={(event) => updateStringList("wizardCantrips", index, event.currentTarget.value)}>
                    {classDetail.wizardSpells.cantrips.map((option) => (
                      <option key={option.value} value={option.value} disabled={draft.wizardCantrips.includes(option.value) && draft.wizardCantrips[index] !== option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              {Array.from({ length: classDetail.wizardSpells.spellbookSpellsKnown }).map((_, index) => (
                <label key={`wizard-spellbook-${index}`}>
                  Spellbook {index + 1}
                  <select value={draft.wizardSpellbookSpells[index] ?? ""} onChange={(event) => updateStringList("wizardSpellbookSpells", index, event.currentTarget.value)}>
                    {classDetail.wizardSpells.spellbookSpells.map((option) => (
                      <option key={option.value} value={option.value} disabled={draft.wizardSpellbookSpells.includes(option.value) && draft.wizardSpellbookSpells[index] !== option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              {Array.from({ length: classDetail.wizardSpells.preparedSpellsKnown }).map((_, index) => (
                <label key={`wizard-prepared-${index}`}>
                  Prepared {index + 1}
                  <select value={draft.wizardPreparedSpells[index] ?? ""} onChange={(event) => updateStringList("wizardPreparedSpells", index, event.currentTarget.value)}>
                    {wizardPreparedOptions(draft, classDetail).map((option) => (
                      <option key={option.value} value={option.value} disabled={draft.wizardPreparedSpells.includes(option.value) && draft.wizardPreparedSpells[index] !== option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          )}
          <label>
            Ability Boost
            <select value={backgroundIncreaseMode} onChange={(event) => updateIncreaseMode(event.currentTarget.value as "twoOne" | "oneEach")}>
              <option value="twoOne">+2 / +1</option>
              <option value="oneEach">+1 / +1 / +1</option>
            </select>
          </label>
          {backgroundIncreaseMode === "twoOne" && (
            <>
              <label>
                +2
                <select value={backgroundPlusTwo ?? ""} onChange={(event) => updateTwoOneIncrease(2, event.currentTarget.value as AbilityType)}>
                  {(backgroundDetail?.abilityScores ?? []).map((option) => (
                    <option key={option.value} value={option.value} disabled={option.value === backgroundPlusOne}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                +1
                <select value={backgroundPlusOne ?? ""} onChange={(event) => updateTwoOneIncrease(1, event.currentTarget.value as AbilityType)}>
                  {(backgroundDetail?.abilityScores ?? []).map((option) => (
                    <option key={option.value} value={option.value} disabled={option.value === backgroundPlusTwo}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          <div className="ability-score-editor">
            <div className="ability-score-editor-meta">
              {draft.abilityScoreMethod === ABILITY_SCORE_METHOD_POINT_BUY && <span>Point Buy {pointBuySpent} / {options.pointBuyPoints}</span>}
              {draft.abilityScoreMethod === ABILITY_SCORE_METHOD_RANDOM && (
                <>
                  <span>Rolled {draft.rolledAbilityScores.join(", ")}</span>
                  <button type="button" onClick={rerollAbilityScores}>Roll</button>
                </>
              )}
            </div>
            {ABILITY_SCORE_OPTIONS.map((ability) => (
              <label key={ability.value}>
                {ability.label}
                <span className="ability-score-select-row">
                  <select value={draft.baseAbilityScores[ability.value]} onChange={(event) => updateBaseAbilityScore(ability.value, Number(event.currentTarget.value))}>
                    {scoreOptionsForMethod(draft.abilityScoreMethod, options, scorePool).map((score) => (
                      <option key={score} value={score} disabled={scoreOptionDisabled(score, ability.value, draft, options, usesScorePool, availableScoreCounts, pointBuySpent)}>
                        {score}
                      </option>
                    ))}
                  </select>
                  <span className="ability-score-total">{draft.baseAbilityScores[ability.value] + draft.backgroundAbilityIncreases[ability.value]}</span>
                </span>
              </label>
            ))}
          </div>
          <button className="builder-submit" type="button" disabled={saving || characterBuilderInvalid} onClick={create}>
            {saving ? "Creating" : "Create Character"}
          </button>
        </div>
      )}
    </section>
  );
}

function defaultCharacterBuilderDraft(playerKey: string): CharacterBuilderDraft {
  return {
    memberId: playerKey.startsWith("player-") ? playerKey : "player-1",
    name: "New Character",
    className: "rogue",
    race: "dwarf",
    background: "criminal",
    abilityScoreMethod: ABILITY_SCORE_METHOD_STANDARD_ARRAY,
    baseAbilityScores: defaultBaseAbilityScores(),
    rolledAbilityScores: [],
    backgroundAbilityIncreases: abilityIncreasesForTwoOne(["dexterity", "constitution", "intelligence"], "dexterity", "constitution"),
    toolProficiency: "thievesTools",
    equipmentChoice: "package",
    magicInitiateSpells: [],
    classSkillProficiencies: [],
    classExpertise: [],
    fightingStyle: "",
    wizardCantrips: [],
    wizardSpellbookSpells: [],
    wizardPreparedSpells: []
  };
}

function defaultBaseAbilityScores(): AbilityScores {
  return {
    strength: 8,
    dexterity: 15,
    constitution: 14,
    intelligence: 13,
    wisdom: 10,
    charisma: 12
  };
}

function abilityLabel(ability: AbilityType): string {
  return ABILITY_SCORE_OPTIONS.find((option) => option.value === ability)?.label ?? ability;
}

function normalizeCharacterBuilderDraft(draft: CharacterBuilderDraft, options: CharacterBuilderOptions): CharacterBuilderDraft {
  const detail = options.backgroundDetails[draft.background];
  const classDetail = options.classDetails[draft.className];
  if (!detail) return draft;
  const toolProficiency = detail.toolOptions.some((option) => option.value === draft.toolProficiency) ? draft.toolProficiency : detail.toolOptions[0]?.value;
  const equipmentChoice = detail.equipmentChoices.some((option) => option.value === draft.equipmentChoice) ? draft.equipmentChoice : detail.equipmentChoices[0]?.value ?? "package";
  const magicInitiateSpells = normalizedMagicInitiateSpells(draft.magicInitiateSpells, detail);
  const classSkillProficiencies = classDetail ? normalizedSelectedOptions(draft.classSkillProficiencies, classDetail.skillProficiencies.options ?? [], classDetail.skillProficiencies.maximum) : [];
  const classExpertise = classDetail ? normalizedSelectedOptions(draft.classExpertise, expertiseOptions({ ...draft, classSkillProficiencies }, classDetail, detail), classDetail.expertise.maximum) : [];
  const fightingStyle = classDetail && classDetail.fightingStyles.maximum > 0
    ? normalizedSelectedOptions([draft.fightingStyle], classDetail.fightingStyles.options ?? [], 1)[0] ?? ""
    : "";
  const wizardCantrips = classDetail ? normalizedSelectedOptions(draft.wizardCantrips, classDetail.wizardSpells.cantrips, classDetail.wizardSpells.cantripsKnown) : [];
  const wizardSpellbookSpells = classDetail ? normalizedSelectedOptions(draft.wizardSpellbookSpells, classDetail.wizardSpells.spellbookSpells, classDetail.wizardSpells.spellbookSpellsKnown) : [];
  const wizardPreparedSpells = classDetail ? normalizedSelectedOptions(draft.wizardPreparedSpells, wizardPreparedOptions({ ...draft, wizardSpellbookSpells }, classDetail), classDetail.wizardSpells.preparedSpellsKnown) : [];
  const abilities = detail.abilityScores.map((option) => option.value as AbilityType);
  const validIncreases = abilities.length > 0 && ABILITY_SCORE_OPTIONS.every((ability) => {
    const increase = draft.backgroundAbilityIncreases[ability.value];
    return increase >= 0 && increase <= 2 && (increase === 0 || abilities.includes(ability.value));
  });
  const totalIncrease = Object.values(draft.backgroundAbilityIncreases).reduce((sum, increase) => sum + increase, 0);
  return {
    ...draft,
    toolProficiency,
    equipmentChoice,
    magicInitiateSpells,
    classSkillProficiencies,
    classExpertise,
    fightingStyle,
    wizardCantrips,
    wizardSpellbookSpells,
    wizardPreparedSpells,
    backgroundAbilityIncreases: validIncreases && totalIncrease === 3 ? draft.backgroundAbilityIncreases : abilityIncreasesForMode("twoOne", abilities)
  };
}

function normalizedSelectedOptions(selectedValues: string[], options: { value: string; label: string }[], count: number): string[] {
  if (count <= 0) return [];
  const selected = selectedValues.filter((value, index, values) => options.some((option) => option.value === value) && values.indexOf(value) === index).slice(0, count);
  for (const option of options) {
    if (selected.length >= count) break;
    if (!selected.includes(option.value)) selected.push(option.value);
  }
  return selected;
}

function expertiseOptions(draft: CharacterBuilderDraft, classDetail?: CharacterBuilderOptions["classDetails"][string], backgroundDetail?: CharacterBuilderOptions["backgroundDetails"][string]) {
  const optionMap = new Map<string, { value: string; label: string }>();
  for (const skill of backgroundDetail?.skillProficiencies ?? []) optionMap.set(skill.value, skill);
  const classSkillOptions = classDetail?.skillProficiencies.options ?? [];
  for (const skill of draft.classSkillProficiencies) {
    optionMap.set(skill, classSkillOptions.find((option) => option.value === skill) ?? { value: skill, label: skillLabel(skill) });
  }
  return [...optionMap.values()];
}

function skillLabel(skill: string): string {
  return skill.replace(/([A-Z])/g, " $1").replace(/^./, (value) => value.toUpperCase());
}

function wizardPreparedOptions(draft: CharacterBuilderDraft, classDetail: CharacterBuilderOptions["classDetails"][string]) {
  const spellbook = new Set(draft.wizardSpellbookSpells);
  const options = classDetail.wizardSpells.spellbookSpells.filter((option) => spellbook.has(option.value));
  return options.length > 0 ? options : classDetail.wizardSpells.preparedSpells;
}

function normalizedMagicInitiateSpells(selectedSpells: string[], detail: CharacterBuilderOptions["backgroundDetails"][string]): string[] {
  const choices = detail.magicInitiateSpellChoices;
  if (!choices) return [];
  const selectedCantrips = selectedSpells.slice(0, choices.cantripsKnown).filter((spellId, index, spells) => choices.cantrips.some((option) => option.value === spellId) && spells.indexOf(spellId) === index);
  const selectedFirstLevel = selectedSpells.slice(choices.cantripsKnown).filter((spellId) => choices.firstLevelSpells.some((option) => option.value === spellId));
  const cantrips = [...selectedCantrips];
  for (const option of choices.cantrips) {
    if (cantrips.length >= choices.cantripsKnown) break;
    if (!cantrips.includes(option.value)) cantrips.push(option.value);
  }
  const firstLevelSpells = selectedFirstLevel.slice(0, choices.firstLevelSpellsKnown);
  for (const option of choices.firstLevelSpells) {
    if (firstLevelSpells.length >= choices.firstLevelSpellsKnown) break;
    if (!firstLevelSpells.includes(option.value)) firstLevelSpells.push(option.value);
  }
  return [...cantrips, ...firstLevelSpells];
}

function selectedMagicInitiateSpellOption(choices: NonNullable<CharacterBuilderOptions["backgroundDetails"][string]["magicInitiateSpellChoices"]>, spellId: string) {
  return [...choices.cantrips, ...choices.firstLevelSpells].find((option) => option.value === spellId);
}

function baseAbilityScoresForMethod(method: string, options: CharacterBuilderOptions, rolledScores: number[]): AbilityScores {
  if (method === ABILITY_SCORE_METHOD_POINT_BUY) {
    return {
      strength: 8,
      dexterity: 15,
      constitution: 14,
      intelligence: 10,
      wisdom: 10,
      charisma: 8
    };
  }
  const pool = method === ABILITY_SCORE_METHOD_RANDOM ? rolledScores : options.standardArray;
  return abilityScoresFromPool(pool.length === 6 ? pool : options.standardArray);
}

function abilityScoresFromPool(pool: number[]): AbilityScores {
  const sorted = [...pool].sort((left, right) => right - left);
  return {
    strength: sorted[5] ?? 8,
    dexterity: sorted[0] ?? 15,
    constitution: sorted[1] ?? 14,
    intelligence: sorted[2] ?? 13,
    wisdom: sorted[4] ?? 10,
    charisma: sorted[3] ?? 12
  };
}

function scoreOptionsForMethod(method: string, options: CharacterBuilderOptions, scorePool: number[]): number[] {
  if (method === ABILITY_SCORE_METHOD_POINT_BUY) {
    return Object.keys(options.pointBuyCosts).map(Number).sort((left, right) => left - right);
  }
  return Array.from(new Set(scorePool)).sort((left, right) => right - left);
}

function scoreOptionDisabled(
  score: number,
  ability: AbilityType,
  draft: CharacterBuilderDraft,
  options: CharacterBuilderOptions,
  usesScorePool: boolean,
  availableScoreCounts: Map<number, number>,
  pointBuySpent: number
): boolean {
  if (!usesScorePool) {
    const currentScore = draft.baseAbilityScores[ability];
    const currentCost = options.pointBuyCosts[String(currentScore)] ?? 0;
    const nextCost = options.pointBuyCosts[String(score)] ?? 0;
    return pointBuySpent - currentCost + nextCost > options.pointBuyPoints;
  }
  return (availableScoreCounts.get(score) ?? 0) === 0;
}

function countScoreValues(scores: number[]): Map<number, number> {
  const counts = new Map<number, number>();
  scores.forEach((score) => counts.set(score, (counts.get(score) ?? 0) + 1));
  return counts;
}

function updatedBaseAbilityScores(draft: CharacterBuilderDraft, ability: AbilityType, nextScore: number): AbilityScores {
  if (draft.abilityScoreMethod === ABILITY_SCORE_METHOD_POINT_BUY) {
    return { ...draft.baseAbilityScores, [ability]: nextScore };
  }
  const currentScore = draft.baseAbilityScores[ability];
  const holder = ABILITY_SCORE_OPTIONS.find((option) => option.value !== ability && draft.baseAbilityScores[option.value] === nextScore)?.value;
  if (!holder) {
    return { ...draft.baseAbilityScores, [ability]: nextScore };
  }
  return {
    ...draft.baseAbilityScores,
    [ability]: nextScore,
    [holder]: currentScore
  };
}

function rollAbilityScorePool(): number[] {
  return Array.from({ length: 6 }, rollAbilityScore);
}

function rollAbilityScore(): number {
  const dice = Array.from({ length: 4 }, () => Math.floor(Math.random() * 6) + 1).sort((left, right) => left - right);
  return dice.slice(1).reduce((sum, die) => sum + die, 0);
}

function abilityIncreasesForMode(mode: "twoOne" | "oneEach", abilities: AbilityType[]): AbilityScores {
  if (mode === "oneEach") {
    return abilityIncreasesFromEntries(abilities.map((ability) => [ability, 1]));
  }
  return abilityIncreasesForTwoOne(abilities, abilities[0], abilities[1]);
}

function abilityIncreasesForTwoOne(abilities: AbilityType[], plusTwo?: AbilityType, plusOne?: AbilityType): AbilityScores {
  const selectedPlusTwo = plusTwo && abilities.includes(plusTwo) ? plusTwo : abilities[0];
  const selectedPlusOne = plusOne && abilities.includes(plusOne) && plusOne !== selectedPlusTwo ? plusOne : abilities.find((ability) => ability !== selectedPlusTwo);
  return abilityIncreasesFromEntries([
    [selectedPlusTwo, 2],
    [selectedPlusOne, 1]
  ]);
}

function abilityIncreasesFromEntries(entries: ([AbilityType | undefined, number])[]): AbilityScores {
  const scores: AbilityScores = {
    strength: 0,
    dexterity: 0,
    constitution: 0,
    intelligence: 0,
    wisdom: 0,
    charisma: 0
  };
  entries.forEach(([ability, increase]) => {
    if (ability) scores[ability] = increase;
  });
  return scores;
}

export function shouldShowCharacterBuilder(isDm: boolean, playerKey: string, sheets: CharacterSheet[]) {
  const occupiedSheets = sheets.filter(isPlayerSlotSheet);
  if (occupiedSheets.length >= 8) return false;
  if (isDm) return true;
  if (!isPlayerSlot(playerKey)) return false;
  return !occupiedSheets.some((sheet) => sheet.id === playerKey || sheet.owner === playerKey);
}

function characterBuilderMemberOptions(isDm: boolean, playerKey: string, sheets: CharacterSheet[]) {
  const occupiedSheets = sheets.filter(isPlayerSlotSheet);
  if (!isDm) {
    return isPlayerSlot(playerKey) && !occupiedSheets.some((sheet) => sheet.id === playerKey || sheet.owner === playerKey)
      ? [{ value: playerKey, label: formatPlayerName(playerKey) }]
      : [];
  }
  return Array.from({ length: 8 }, (_value, index) => {
    const value = `player-${index + 1}`;
    return occupiedSheets.some((sheet) => sheet.id === value || sheet.owner === value) ? null : { value, label: value };
  }).filter((option): option is { value: string; label: string } => option !== null);
}

function isPlayerSlotSheet(sheet: CharacterSheet) {
  return isPlayerSlot(sheet.id) || isPlayerSlot(sheet.owner);
}

function isPlayerSlot(playerKey: string) {
  return /^player-[1-8]$/.test(playerKey);
}

function formatPlayerName(playerKey: string) {
  return playerKey.replace("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
