import type { AbilityType } from "../types";

export const SAME_ABILITY_VALUE = "__same__";

export const ABILITY_SCORE_OPTIONS: { value: AbilityType; label: string }[] = [
  { value: "strength", label: "Strength" },
  { value: "dexterity", label: "Dexterity" },
  { value: "constitution", label: "Constitution" },
  { value: "intelligence", label: "Intelligence" },
  { value: "wisdom", label: "Wisdom" },
  { value: "charisma", label: "Charisma" }
];
