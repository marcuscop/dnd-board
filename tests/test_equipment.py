from dnd_board.character_sheet import CurrencyUnit, DamageType, DiceType, EquipmentSlot, EquipmentType, Money, WeaponProperty, enum_key
from dnd_board.rules.backgrounds import BackgroundDefinition, BackgroundEquipmentChoice, BackgroundEquipmentGrant, BackgroundType, ToolType, background_definition, background_equipment, background_equipment_grant_item, background_feat_feature, background_features, background_features_for_tool, background_purse, purse_from_money
from dnd_board.rules.equipment import (
    EquipmentCategory,
    EquipmentCostType,
    EquipmentId,
    WeaponMastery,
    equipment_definition,
    equipment_item,
    equipment_type_for_category,
    fixed_cost,
)


def test_equipment_catalog_models_background_weapons() -> None:
    dagger = equipment_definition(EquipmentId.DAGGER)
    shortbow = equipment_definition("shortbow")

    assert dagger is not None
    assert dagger.damageDiceCount == 1
    assert dagger.damageDiceType == DiceType.D4
    assert dagger.damageType == DamageType.PIERCING
    assert dagger.properties == (WeaponProperty.FINESSE, WeaponProperty.LIGHT, WeaponProperty.THROWN)
    assert dagger.normalRangeFeet == 20
    assert dagger.longRangeFeet == 60
    assert dagger.mastery == WeaponMastery.NICK
    assert dagger.cost.type == EquipmentCostType.FIXED
    assert dagger.cost.money is not None
    assert dagger.cost.money.quantity == 2
    assert dagger.cost.money.unit == CurrencyUnit.GP
    assert dagger.costLabel == "2 GP"

    assert shortbow is not None
    assert shortbow.properties == (WeaponProperty.AMMUNITION, WeaponProperty.TWO_HANDED)
    assert shortbow.normalRangeFeet == 80
    assert shortbow.longRangeFeet == 320


def test_equipment_category_derives_sheet_item_type() -> None:
    assert equipment_type_for_category(EquipmentCategory.WEAPON) == EquipmentType.WEAPON
    assert equipment_type_for_category(EquipmentCategory.ARMOR) == EquipmentType.ARMOR
    assert equipment_type_for_category(EquipmentCategory.SHIELD) == EquipmentType.SHIELD
    assert equipment_type_for_category(EquipmentCategory.ADVENTURING_GEAR) == EquipmentType.GEAR
    assert equipment_definition(EquipmentId.ARCANE_FOCUS).costLabel == "Varies"
    assert fixed_cost(7, CurrencyUnit.SP).label == "7 SP"


def test_equipment_catalog_adapts_to_sheet_items() -> None:
    spear = equipment_item(EquipmentId.SPEAR, quantity=2)

    assert spear is not None
    assert spear.id == enum_key(EquipmentId.SPEAR)
    assert spear.name == "Spear"
    assert spear.quantity == 2
    assert spear.weight == 6
    assert spear.itemType == EquipmentType.WEAPON
    assert spear.slot == EquipmentSlot.CARRIED
    assert equipment_item("missing") is None


def test_background_equipment_package_is_itemized_with_selected_tool() -> None:
    items = background_equipment(BackgroundType.CRIMINAL, BackgroundEquipmentChoice.PACKAGE, ToolType.THIEVES_TOOLS)
    by_name = {item.name: item for item in items}

    assert by_name["Dagger"].quantity == 2
    assert by_name["Dagger"].itemType == EquipmentType.WEAPON
    assert by_name["Thieves' Tools"].id == enum_key(ToolType.THIEVES_TOOLS)
    assert by_name["Crowbar"].quantity == 1
    assert by_name["Pouch"].quantity == 2
    assert by_name["Traveler's Clothes"].weight == 4
    assert "GP" not in by_name
    assert background_purse(BackgroundType.CRIMINAL, BackgroundEquipmentChoice.PACKAGE).gold == 16
    assert background_purse(BackgroundType.CRIMINAL, BackgroundEquipmentChoice.PACKAGE).silver == 0
    assert background_purse(BackgroundType.CRIMINAL, BackgroundEquipmentChoice.PACKAGE).copper == 0
    assert background_purse(BackgroundType.CRIMINAL, BackgroundEquipmentChoice.GOLD).gold == 50


def test_background_equipment_grants_cover_selected_tools_money_and_empty_values() -> None:
    assert background_equipment(BackgroundType.ARTISAN, BackgroundEquipmentChoice.GOLD, ToolType.CARPENTERS_TOOLS) == []
    assert background_equipment_grant_item(BackgroundEquipmentGrant(selectedTool=True), None) is None
    assert background_equipment_grant_item(BackgroundEquipmentGrant(money=Money(2, CurrencyUnit.SP))) is None
    assert background_equipment_grant_item(BackgroundEquipmentGrant()) is None

    selected = background_equipment_grant_item(BackgroundEquipmentGrant(selectedTool=True, quantity=2), ToolType.CARPENTERS_TOOLS)
    assert selected is not None
    assert selected.name == "Carpenter's Tools"
    assert selected.quantity == 2

    purse = purse_from_money([Money(1, CurrencyUnit.CP), Money(2, CurrencyUnit.SP), Money(3, CurrencyUnit.GP)])
    assert (purse.copper, purse.silver, purse.gold) == (1, 2, 3)
    assert purse_from_money([Money(4, None)]).gold == 0


def test_background_features_cover_missing_and_default_tool_paths(monkeypatch) -> None:
    assert background_features_for_tool(BackgroundType.CRIMINAL, None) == []
    assert background_features(BackgroundType.ARTISAN)[0].description == "Gain proficiency with Alchemist's Supplies."
    assert background_feat_feature(BackgroundDefinition(BackgroundType.CRIMINAL, source=None)) is None
    monkeypatch.setattr("dnd_board.rules.backgrounds.general_feat_feature", lambda _key: None)
    assert background_feat_feature(BackgroundDefinition(BackgroundType.CRIMINAL, source=None, feat=background_definition(BackgroundType.CRIMINAL).feat)) is None
