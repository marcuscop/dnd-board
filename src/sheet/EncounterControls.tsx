import { useMemo, useState } from "react";

import type { CharacterSheet, EncounterParticipant, EncounterState, ResourceId, Token } from "../types";

type EncounterControlsProps = {
  encounter: EncounterState | null;
  isDm: boolean;
  playerKey: string;
  roomId: string;
  sheets: CharacterSheet[];
  tokens: Token[];
  onEncounterChange: (encounter: EncounterState | null) => void;
};

export function EncounterControls({ encounter, isDm, playerKey, roomId, sheets, tokens, onEncounterChange }: EncounterControlsProps) {
  const [setupOpen, setSetupOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<EncounterParticipant[]>([]);
  const sheetsById = useMemo(() => new Map(sheets.map((sheet) => [sheet.id, sheet])), [sheets]);
  const tokensById = useMemo(() => new Map(tokens.map((token) => [token.id, token])), [tokens]);
  const currentSheet = encounter ? sheetsById.get(encounter.currentParticipantId) : undefined;
  const canEndTurn = encounter && (isDm || currentSheet?.owner === playerKey);

  const openSetup = () => {
    const initial = encounter?.participants ?? sheets
      .filter((sheet) => tokensById.get(sheet.tokenId)?.inScene)
      .map((sheet) => ({ participantId: sheet.id, initiative: 0 }));
    setParticipants(initial);
    setSetupOpen(true);
  };

  const toggleParticipant = (participantId: string) => {
    setParticipants((current) => current.some((entry) => entry.participantId === participantId)
      ? current.filter((entry) => entry.participantId !== participantId)
      : [...current, { participantId, initiative: 0 }]);
  };

  const setInitiative = (participantId: string, initiative: number) => {
    setParticipants((current) => current
      .map((entry) => entry.participantId === participantId ? { ...entry, initiative } : entry)
      .sort((left, right) => right.initiative - left.initiative));
  };

  const moveParticipant = (index: number, delta: -1 | 1) => {
    setParticipants((current) => {
      const destination = index + delta;
      if (destination < 0 || destination >= current.length) return current;
      const next = [...current];
      [next[index], next[destination]] = [next[destination], next[index]];
      return next;
    });
  };

  const rollInitiative = async () => {
    if (!participants.length) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/encounter/initiative?playerKey=${encodeURIComponent(playerKey)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(participants.map((entry) => entry.participantId))
      });
      if (!response.ok) throw new Error(await response.text());
      const result = await response.json() as { initiatives: { participantId: string; total: number }[] };
      const totals = new Map(result.initiatives.map((entry) => [entry.participantId, entry.total]));
      setParticipants((current) => current
        .map((entry) => ({ ...entry, initiative: totals.get(entry.participantId) ?? entry.initiative }))
        .sort((left, right) => right.initiative - left.initiative));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to roll initiative");
    } finally {
      setBusy(false);
    }
  };

  const saveEncounter = async () => {
    if (!participants.length) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/encounter?playerKey=${encodeURIComponent(playerKey)}`, {
        method: encounter ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(participants)
      });
      if (!response.ok) throw new Error(await response.text());
      const result = await response.json() as { encounter: EncounterState };
      onEncounterChange(result.encounter);
      setSetupOpen(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save encounter");
    } finally {
      setBusy(false);
    }
  };

  const advance = async () => {
    if (!encounter) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/encounter/advance?playerKey=${encodeURIComponent(playerKey)}&turnId=${encodeURIComponent(encounter.turnId)}`, { method: "POST" });
      if (!response.ok) throw new Error(await response.text());
      const result = await response.json() as { encounter: EncounterState };
      onEncounterChange(result.encounter);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to advance turn");
    } finally {
      setBusy(false);
    }
  };

  const adjustBudget = async (participantId: string, resource: ResourceId, current: number) => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(roomId)}/encounter/participants/${encodeURIComponent(participantId)}/resources/${resource}?playerKey=${encodeURIComponent(playerKey)}&current=${current}`,
        { method: "POST" }
      );
      if (!response.ok) throw new Error(await response.text());
      const result = await response.json() as { encounter: EncounterState };
      onEncounterChange(result.encounter);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to adjust encounter resource");
    } finally {
      setBusy(false);
    }
  };

  const end = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/encounter?playerKey=${encodeURIComponent(playerKey)}`, { method: "DELETE" });
      if (!response.ok) throw new Error(await response.text());
      onEncounterChange(null);
      setSetupOpen(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to end encounter");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="encounter-controls">
      {encounter && (
        <div className="encounter-bar">
          <strong>Round {encounter.round}</strong>
          <ol className="encounter-queue">
            {encounter.participants.map((participant) => {
              const sheet = sheetsById.get(participant.participantId);
              const token = tokensById.get(sheet?.tokenId ?? participant.participantId);
              return (
                <li className={participant.participantId === encounter.currentParticipantId ? "current" : ""} key={participant.participantId}>
                  {(token?.avatarUrl || sheet?.avatarUrl) && <img alt="" src={token?.avatarUrl || sheet?.avatarUrl} />}
                  <span className="encounter-name">{sheet?.name ?? participant.participantId}</span>
                  <span>{participant.initiative}</span>
                </li>
              );
            })}
          </ol>
          {canEndTurn && <button disabled={busy || encounter.status !== "active"} onClick={advance}>End Turn</button>}
        </div>
      )}
      {isDm && <button disabled={busy} onClick={openSetup}>{encounter ? "Edit Encounter" : "Encounter"}</button>}
      {isDm && encounter && <button className="danger-button" disabled={busy} onClick={end}>End Encounter</button>}
      {error && !setupOpen && <div className="encounter-error" role="alert">{error}</div>}
      {setupOpen && isDm && (
        <div className="encounter-setup" role="dialog" aria-label="Encounter setup">
          {error && <div className="encounter-error" role="alert">{error}</div>}
          <div className="encounter-setup-heading">
            <strong>{encounter ? "Edit Encounter" : "Start Encounter"}</strong>
            <button aria-label="Close encounter setup" onClick={() => setSetupOpen(false)}>×</button>
          </div>
          <div className="encounter-participant-picker">
            {sheets.map((sheet) => (
              <label key={sheet.id}>
                <input checked={participants.some((entry) => entry.participantId === sheet.id)} onChange={() => toggleParticipant(sheet.id)} type="checkbox" />
                {sheet.name}
              </label>
            ))}
          </div>
          <div className="encounter-order">
            {participants.map((participant, index) => (
              <div key={participant.participantId}>
                <span>{sheetsById.get(participant.participantId)?.name ?? participant.participantId}</span>
                <input aria-label={`${participant.participantId} initiative`} onChange={(event) => setInitiative(participant.participantId, Number(event.target.value))} type="number" value={participant.initiative} />
                <button aria-label="Move earlier" disabled={index === 0} onClick={() => moveParticipant(index, -1)}>↑</button>
                <button aria-label="Move later" disabled={index === participants.length - 1} onClick={() => moveParticipant(index, 1)}>↓</button>
              </div>
            ))}
          </div>
          {encounter && (
            <div className="encounter-budgets">
              {encounter.participantStates.map((participant) => (
                <div key={participant.participantId}>
                  <span>{sheetsById.get(participant.participantId)?.name ?? participant.participantId}</span>
                  {participant.resources.map((resource) => (
                    <span className="encounter-budget" key={resource.resource}>
                      {resource.resource}
                      <button disabled={busy || resource.current === 0} onClick={() => adjustBudget(participant.participantId, resource.resource, resource.current - 1)}>-</button>
                      <strong>{resource.current}/{resource.maximum}</strong>
                      <button disabled={busy || resource.current === resource.maximum} onClick={() => adjustBudget(participant.participantId, resource.resource, resource.current + 1)}>+</button>
                    </span>
                  ))}
                </div>
              ))}
            </div>
          )}
          <div className="encounter-setup-actions">
            <button disabled={busy || !participants.length} onClick={rollInitiative}>Roll Initiative</button>
            <button disabled={busy || !participants.length} onClick={saveEncounter}>{encounter ? "Apply" : "Start"}</button>
          </div>
        </div>
      )}
    </div>
  );
}
