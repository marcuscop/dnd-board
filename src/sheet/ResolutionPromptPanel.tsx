import type { ResolutionInterceptorPrompt } from "../types";

type ResolutionPromptPanelProps = {
  isDm: boolean;
  prompts: ResolutionInterceptorPrompt[];
  onRespond: (prompt: ResolutionInterceptorPrompt, use: boolean) => void;
};

export function ResolutionPromptPanel({ isDm, prompts, onRespond }: ResolutionPromptPanelProps) {
  if (prompts.length === 0) return null;

  return (
    <section className="sheet-panel resolution-prompt-panel">
      <div className="panel-title-row">
        <h2>Interruptions</h2>
        <span>{prompts.length}</span>
      </div>
      <div className="resolution-prompt-list">
        {prompts.map((prompt) => (
          <article className="resolution-prompt-card" key={prompt.id}>
            <div>
              <strong>{prompt.label}</strong>
              <span>{prompt.ownerName}{isDm ? " · DM override available" : ""}</span>
              <p>{prompt.description}</p>
            </div>
            <div className="resolution-prompt-actions">
              <button onClick={() => onRespond(prompt, true)}>{prompt.useLabel}</button>
              <button onClick={() => onRespond(prompt, false)}>{prompt.declineLabel}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
