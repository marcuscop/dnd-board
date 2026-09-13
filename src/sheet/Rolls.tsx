import { RollLogEntryType, RollResolutionMode } from "../types";
import type { CharacterSheet, RollLogEntry, RollPayload } from "../types";

export function RollCard({
  compact = false,
  roll,
  draggable,
  onDragEnd,
  onDragStart
}: {
  compact?: boolean;
  roll: RollPayload;
  roller: CharacterSheet | undefined;
  draggable: boolean;
  onDragEnd: () => void;
  onDragStart: (preserveRoll: boolean) => void;
}) {
  const rollParentLabel = roll.sourceLabel && roll.sourceLabel !== roll.label ? roll.sourceLabel : roll.source.sectionLabel;

  return (
    <li
      className={["roll-card", draggable ? "draggable" : "", compact ? "compact" : ""].filter(Boolean).join(" ")}
      draggable={draggable}
      onPointerDown={(event) => {
        if (!draggable || !event.shiftKey || event.button !== 0) return;
        event.preventDefault();
        event.stopPropagation();
        const source = event.currentTarget;
        const rect = source.getBoundingClientRect();
        const pointerOffsetX = event.clientX - rect.left;
        const pointerOffsetY = event.clientY - rect.top;
        const ghost = source.cloneNode(true) as HTMLElement;
        ghost.classList.add("roll-pointer-ghost");
        ghost.style.width = `${rect.width}px`;
        ghost.style.left = "0";
        ghost.style.top = "0";
        document.body.appendChild(ghost);
        onDragStart(true);

        const moveGhost = (clientX: number, clientY: number) => {
          ghost.style.transform = `translate(${clientX - pointerOffsetX}px, ${clientY - pointerOffsetY}px)`;
        };
        const handlePointerMove = (moveEvent: PointerEvent) => moveGhost(moveEvent.clientX, moveEvent.clientY);
        const handlePointerUp = (upEvent: PointerEvent) => {
          window.removeEventListener("pointermove", handlePointerMove);
          ghost.remove();
          onDragEnd();
          const target = document.elementFromPoint(upEvent.clientX, upEvent.clientY)?.closest<HTMLElement>("[data-roll-drop-sheet-id]");
          if (!target?.dataset.rollDropSheetId) return;
          window.dispatchEvent(new CustomEvent("roll-card-shift-drop", { detail: { rollId: roll.id, targetSheetId: target.dataset.rollDropSheetId } }));
        };
        moveGhost(event.clientX, event.clientY);
        window.addEventListener("pointermove", handlePointerMove);
        window.addEventListener("pointerup", handlePointerUp, { once: true });
      }}
      onDragEnd={(event) => {
        event.currentTarget.classList.remove("drag-source-hidden");
        onDragEnd();
      }}
      onDragStart={(event) => {
        const element = event.currentTarget;
        event.dataTransfer.effectAllowed = "copy";
        event.dataTransfer.setData("text/plain", roll.id);
        onDragStart(event.shiftKey);
        window.requestAnimationFrame(() => element.classList.add("drag-source-hidden"));
      }}
    >
      <span className="die-badge">
        <img src={diceImagePath(roll.diceType)} alt="" draggable={false} />
        <strong>{roll.total}</strong>
      </span>
      <span className="roll-main">
        <strong>{roll.label}</strong>
        <small>{rollDamageTypeLabel(roll) ? `${rollParentLabel} · ${rollDamageTypeLabel(roll)}` : rollParentLabel}</small>
      </span>
      {!compact && <span className="roll-total roll-result-number">{rollMathText(roll)}</span>}
    </li>
  );
}

export function RollLogRow({ entry, roller }: { entry: RollLogEntry; roller: CharacterSheet | undefined }) {
  const roll = entry.roll;
  const displayRoll = entry.resolution?.roll ?? roll;
  const actor = roller?.name ?? formatPlayerName(roll.roller);
  const isBlocked = entry.entryType === RollLogEntryType.ROLL_BLOCKED;
  const isLogOnly = roll.source.actionId === "log";
  const responseRollText = entry.resolution?.responseRolls?.length
    ? ` · ${entry.resolution.responseRolls.map((responseRoll) => `${responseRoll.label} ${rollMathText(responseRoll)}`).join(" · ")}`
    : "";

  return (
    <li className="roll-log-row">
      <time dateTime={logEntryDate(entry).toISOString()}>{formatLogTime(entry)}</time>
      <span>
        <strong>{roll.sourceLabel}</strong>
        {isBlocked
          ? ` ${actor}: ${roll.label}`
          : entry.resolution
          ? ` ${actor}: ${displayRoll.label} ${rollMathText(displayRoll)}${responseRollText}; ${entry.resolution.outcome} to ${entry.resolution.targetName}`
          : ` ${actor}: ${roll.label} `}
        {!entry.resolution && !isBlocked && !isLogOnly && <span className="roll-result-number">{rollMathText(roll)}</span>}
        {roll.resourcesSpent
          ? roll.resourcesSpent.map((resource) => ` · ${resource.label} ${resource.current}/${resource.maximum}`).join("")
          : ""}
      </span>
    </li>
  );
}

export function InlineRolls({
  pendingRolls,
  resolvedRolls = [],
  roller,
  rollDraggable,
  onDragRollEnd,
  onDragRollStart
}: {
  pendingRolls: RollPayload[];
  resolvedRolls?: RollLogEntry[];
  roller: CharacterSheet;
  rollDraggable: boolean;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string, preserveRoll: boolean) => void;
}) {
  if (pendingRolls.length === 0 && resolvedRolls.length === 0) return null;

  return (
    <div className="inline-rolls">
      {pendingRolls.map((pendingRoll) => (
        <RollCard
          key={pendingRoll.id}
          roll={pendingRoll}
          roller={roller}
          draggable={rollDraggable && isTargetableRoll(pendingRoll)}
          compact
          onDragEnd={onDragRollEnd}
          onDragStart={(preserveRoll) => onDragRollStart(pendingRoll.id, preserveRoll)}
        />
      ))}
      {resolvedRolls.map((entry) => (
        <RollCard
          key={entry.id}
          roll={entry.roll}
          roller={roller}
          draggable={false}
          compact
          onDragEnd={onDragRollEnd}
          onDragStart={() => undefined}
        />
      ))}
    </div>
  );
}

export function isTargetableRoll(roll: RollPayload | undefined) {
  if (!roll) return false;
  if ([
    RollResolutionMode.ATTACK_VS_ARMOR_CLASS,
    RollResolutionMode.APPLY_DAMAGE,
    RollResolutionMode.HEAL_SELF,
    RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS,
  ].includes(roll.resolution)) {
    return true;
  }
  return Boolean((roll.damageSavingThrow && roll.damageSaveDc) || roll.pendingEffect !== undefined);
}

function rollMathText(roll: RollPayload) {
  const advantageText = rollAdvantageText(roll);
  const dice = rollDieText(roll);
  const modifierParts = (roll.modifierBreakdown ?? []).filter((part) => part.value !== 0);
  const modifiers = modifierParts.length
    ? modifierParts.map((part) => `${part.value >= 0 ? "+" : "-"} ${part.source} (${Math.abs(part.value)})`).join(" ")
    : formatSigned(roll.modifier);
  if (roll.damageComponents?.length) {
    const components = roll.damageComponents
      .map((component) => `${component.damageTypeLabel ?? cleanName(component.damageType)} ${rollComponentMathText(component)}`)
      .join(" + ");
    if (roll.resolution === RollResolutionMode.ATTACK_VS_ARMOR_CLASS) {
      const damageTotal = roll.damageComponents.reduce((total, component) => total + component.total, 0);
      return `Attack ${dice} ${modifiers} = ${roll.total}${advantageText}${roll.criticalHit ? " (Critical Hit)" : ""}; Damage ${components} = ${damageTotal}`;
    }
    return `${components} = ${roll.total}${advantageText}`;
  }
  return `${dice} ${modifiers} = ${roll.total}${advantageText}`;
}

function rollAdvantageText(roll: RollPayload) {
  const parts = [
    roll.advantageConditionsLabel?.length ? `Advantage: ${roll.advantageConditionsLabel.join(", ")}` : "",
    roll.disadvantageConditionsLabel?.length ? `Disadvantage: ${roll.disadvantageConditionsLabel.join(", ")}` : "",
  ].filter(Boolean);
  return parts.length ? ` (${parts.join("; ")})` : "";
}

function rollComponentMathText(component: NonNullable<RollPayload["damageComponents"]>[number]) {
  const modifierParts = (component.modifierBreakdown ?? []).filter((part) => part.value !== 0);
  const modifiers = modifierParts.length
    ? ` ${modifierParts.map((part) => `${part.value >= 0 ? "+" : "-"} ${part.source} (${Math.abs(part.value)})`).join(" ")}`
    : component.modifier !== 0 ? ` ${formatSigned(component.modifier)}` : "";
  return `${component.dice.join("+")}${modifiers}`;
}

function rollDamageTypeLabel(roll: RollPayload) {
  if (roll.damageComponents?.length) {
    return roll.damageComponents.map((component) => component.damageTypeLabel ?? cleanName(component.damageType)).join(" + ");
  }
  return roll.damageTypeLabel ?? "";
}

function rollDieText(roll: RollPayload) {
  if (roll.dice.length === 2 && roll.die === "2d20kh1") return `${roll.dice.join(", ")} keep ${Math.max(...roll.dice)}`;
  if (roll.dice.length === 2 && roll.die === "2d20kl1") return `${roll.dice.join(", ")} keep ${Math.min(...roll.dice)}`;
  return roll.dice.join("+");
}

function diceImagePath(diceType: RollPayload["diceType"]) {
  return `/${diceType}.png`;
}

function formatLogTime(entry: RollLogEntry) {
  return logEntryDate(entry).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

function logEntryDate(entry: RollLogEntry) {
  return new Date(Math.floor(entry.createdAt / 1_000_000));
}

function formatPlayerName(playerKey: string) {
  if (playerKey === "dm") return "DM";
  return playerKey.replace("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatSigned(value: number) {
  return value >= 0 ? `+${value}` : String(value);
}

function cleanName(identifier: string) {
  return identifier.replace(/([A-Z])/g, " $1").replace(/[-_]/g, " ").replace(/\b\w/g, (match) => match.toUpperCase()).trim();
}
