import { useState } from "react";

import type { CharacterSheet, ResourceId } from "../types";

export type RestHitDieSelection = {
  sheetId: string;
  resourceId: ResourceId;
  count: number;
};

type RestControlsProps = {
  sheets: CharacterSheet[];
  disabled: boolean;
  onRest: (rest: "short" | "long", hitDice?: RestHitDieSelection[]) => Promise<boolean>;
};

export function RestControls({ sheets, disabled, onRest }: RestControlsProps) {
  const [mode, setMode] = useState<"short" | "long" | null>(null);
  const [selections, setSelections] = useState<RestHitDieSelection[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const setCount = (sheetId: string, resourceId: ResourceId, count: number) => {
    setSelections((current) => [
      ...current.filter((selection) => selection.sheetId !== sheetId || selection.resourceId !== resourceId),
      ...(count > 0 ? [{ sheetId, resourceId, count }] : [])
    ]);
  };

  const submit = async () => {
    if (!mode || submitting) return;
    setSubmitting(true);
    try {
      if (await onRest(mode, mode === "short" ? selections : [])) {
        setMode(null);
        setSelections([]);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rest-actions">
      <button type="button" disabled={disabled} onClick={() => setMode(mode === "short" ? null : "short")}>Short Rest</button>
      <button type="button" disabled={disabled} onClick={() => setMode(mode === "long" ? null : "long")}>Long Rest</button>
      {mode && (
        <div className="rest-panel" role="dialog" aria-label={`${mode === "short" ? "Short" : "Long"} Rest`}>
          <div className="rest-panel-heading">
            <strong>{mode === "short" ? "Short Rest" : "Long Rest"}</strong>
            <button type="button" aria-label="Close rest panel" title="Close" onClick={() => setMode(null)}>X</button>
          </div>
          <div className="rest-panel-characters">
            {sheets.filter((sheet) => sheet.hp.current > 0).map((sheet) => (
              <div className="rest-panel-character" key={sheet.id}>
                <div className="rest-panel-character-heading">
                  <span>{sheet.name}</span>
                  <span>{sheet.hp.current}/{sheet.hp.max} HP</span>
                </div>
                {mode === "short" && sheet.resources.filter((resource) => resource.kind === "hitDie" && resource.currentUses > 0).map((resource) => (
                  <label className="rest-hit-die-row" key={resource.id}>
                    <span>{resource.name} ({resource.currentUses})</span>
                    <input
                      type="number"
                      min={0}
                      max={resource.currentUses}
                      value={selections.find((selection) => selection.sheetId === sheet.id && selection.resourceId === resource.resource)?.count ?? 0}
                      onChange={(event) => setCount(sheet.id, resource.resource, Math.max(0, Math.min(resource.currentUses, Number(event.target.value) || 0)))}
                    />
                  </label>
                ))}
              </div>
            ))}
          </div>
          <div className="rest-panel-actions">
            <button type="button" onClick={() => setMode(null)}>Cancel</button>
            <button type="button" disabled={submitting || disabled} onClick={submit}>{submitting ? "Resting..." : "Complete Rest"}</button>
          </div>
        </div>
      )}
    </div>
  );
}
