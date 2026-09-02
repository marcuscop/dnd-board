from dnd_board.character_sheet import AbilityType, CurrencyUnit, enum_key
from dnd_board.rules.backgrounds import ToolType
from dnd_board.rules.equipment import EquipmentCostType
from dnd_board.rules.tools import ToolCategory, serialized_tool_details, tool_definition, tool_definitions


def test_tool_catalog_contains_2024_tool_mechanics() -> None:
    tools = tool_definitions()

    assert set(tools) >= set(ToolType)
    assert tool_definition(ToolType.CARPENTERS_TOOLS).category == ToolCategory.ARTISAN
    assert tool_definition(ToolType.CARPENTERS_TOOLS).ability == AbilityType.STRENGTH
    assert tool_definition(ToolType.CARPENTERS_TOOLS).weightLb == 6
    assert tool_definition(ToolType.CARPENTERS_TOOLS).cost.type == EquipmentCostType.FIXED
    assert tool_definition(ToolType.CARPENTERS_TOOLS).cost.money is not None
    assert tool_definition(ToolType.CARPENTERS_TOOLS).cost.money.quantity == 8
    assert tool_definition(ToolType.CARPENTERS_TOOLS).cost.money.unit == CurrencyUnit.GP
    assert tool_definition(ToolType.CARPENTERS_TOOLS).costLabel == "8 GP"
    assert tool_definition(ToolType.CARPENTERS_TOOLS).utilizeActions[0].dc == 20
    assert "Portable Ram" in tool_definition(ToolType.CARPENTERS_TOOLS).craftOutputs

    assert tool_definition(ToolType.THIEVES_TOOLS).ability == AbilityType.DEXTERITY
    assert {action.description for action in tool_definition(ToolType.THIEVES_TOOLS).utilizeActions} == {"Pick a lock", "Disarm a trap"}
    assert tool_definition(ToolType.POISONERS_KIT).craftOutputs == ("Basic Poison",)


def test_tool_catalog_models_variant_parents() -> None:
    gaming_set = tool_definition(ToolType.GAMING_SET)
    dice = tool_definition(ToolType.DICE_SET)
    instrument = tool_definition(ToolType.MUSICAL_INSTRUMENT)
    lute = tool_definition(ToolType.LUTE)

    assert gaming_set.hasVariants is True
    assert dice.variantParent == ToolType.GAMING_SET
    assert dice.category == ToolCategory.GAMING_SET
    assert instrument.hasVariants is True
    assert lute.variantParent == ToolType.MUSICAL_INSTRUMENT
    assert lute.ability == AbilityType.CHARISMA


def test_serialized_tool_details_are_builder_ready() -> None:
    details = serialized_tool_details()
    thieves_tools = details[enum_key(ToolType.THIEVES_TOOLS)]

    assert thieves_tools["category"] == "Other Tools"
    assert thieves_tools["ability"] == enum_key(AbilityType.DEXTERITY)
    assert thieves_tools["weightLb"] == 1
    assert thieves_tools["cost"] == "25 GP"
    assert thieves_tools["utilizeActions"] == [
        {"description": "Pick a lock", "dc": 15},
        {"description": "Disarm a trap", "dc": 15},
    ]
    assert thieves_tools["craftOutputs"] == []
