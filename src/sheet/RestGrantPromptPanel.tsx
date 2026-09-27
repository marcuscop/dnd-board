import { useState } from "react";
import type { RestGrantPrompt } from "../types";

export function RestGrantPromptPanel({ prompts, onRespond }: {
  prompts: RestGrantPrompt[];
  onRespond: (prompt: RestGrantPrompt, targetSheetIds: string[]) => void;
}) {
  if (prompts.length === 0) return null;
  return (
    <section className="sheet-panel resolution-prompt-panel">
      <div className="panel-title-row">
        <h2>Rest Decisions</h2>
        <span>{prompts.length}</span>
      </div>
      {prompts.map((prompt) => (
        <RestGrantPromptRow key={prompt.id} prompt={prompt} onRespond={onRespond} />
      ))}
    </section>
  );
}

function RestGrantPromptRow({ prompt, onRespond }: {
  prompt: RestGrantPrompt;
  onRespond: (prompt: RestGrantPrompt, targetSheetIds: string[]) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  return (
    <div className="rest-grant-prompt">
      <div className="rest-grant-prompt-heading">
        <strong>{prompt.label}</strong>
        <span>{prompt.sourceName} · up to {prompt.maximumTargets} allies</span>
      </div>
      <div className="rest-grant-targets">
        {prompt.targets.map((target) => (
          <label key={target.sheetId}>
            <input
              type="checkbox"
              checked={selected.includes(target.sheetId)}
              disabled={!selected.includes(target.sheetId) && selected.length >= prompt.maximumTargets}
              onChange={(event) => setSelected((current) => event.currentTarget.checked
                ? [...current, target.sheetId]
                : current.filter((id) => id !== target.sheetId))}
            />
            {target.name}
          </label>
        ))}
      </div>
      <div className="resolution-prompt-actions">
        <button type="button" disabled={selected.length === 0} onClick={() => onRespond(prompt, selected)}>Grant</button>
        <button type="button" onClick={() => onRespond(prompt, [])}>Pass</button>
      </div>
    </div>
  );
}
