import { useState } from "react";

import type { DiceType, RollPayload } from "../types";
import { RollCard } from "./Rolls";

const DICE_TYPES: DiceType[] = ["d4", "d6", "d8", "d10", "d12", "d20"];

export function AdHocDiceRoller({ onRoll }: { onRoll: (dice: DiceType, count: number) => Promise<RollPayload | null> }) {
  const [counts, setCounts] = useState<Record<DiceType, number>>({ d4: 1, d6: 1, d8: 1, d10: 1, d12: 1, d20: 1 });
  const [lastRolls, setLastRolls] = useState<Partial<Record<DiceType, RollPayload>>>({});
  const [rollingDice, setRollingDice] = useState<DiceType | null>(null);

  const updateCount = (dice: DiceType, delta: 1 | -1) => {
    setCounts((current) => ({ ...current, [dice]: Math.min(20, Math.max(1, current[dice] + delta)) }));
  };
  const rollDice = async (dice: DiceType) => {
    setRollingDice(dice);
    try {
      const roll = await onRoll(dice, counts[dice]);
      if (roll) setLastRolls((current) => ({ ...current, [dice]: roll }));
    } finally {
      setRollingDice(null);
    }
  };

  return (
    <section className="ad-hoc-dice-roller">
      <button className="ad-hoc-dice-handle" aria-label="Open dice roller" type="button">&lt;</button>
      <div className="ad-hoc-dice-panel">
        <h2>Dice Roller</h2>
        <div className="ad-hoc-dice-list">
          {DICE_TYPES.map((dice) => {
            const lastRoll = lastRolls[dice];
            return (
              <div className="ad-hoc-dice-row" key={dice}>
                <button className="ad-hoc-roll-button" disabled={rollingDice === dice} onClick={() => rollDice(dice)} type="button">Roll {dice.toUpperCase()}</button>
                <div className="ad-hoc-count-controls" aria-label={`${dice} count`}>
                  <button disabled={counts[dice] <= 1} onClick={() => updateCount(dice, -1)} type="button">-</button>
                  <strong>{counts[dice]}</strong>
                  <button disabled={counts[dice] >= 20} onClick={() => updateCount(dice, 1)} type="button">+</button>
                </div>
                <ol className="ad-hoc-result-slot" aria-live="polite">
                  {lastRoll ? <RollCard compact={false} roll={lastRoll} roller={undefined} draggable={false} onDragEnd={() => undefined} onDragStart={() => undefined} /> : <span>-</span>}
                </ol>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
