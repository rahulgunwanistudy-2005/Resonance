import { useState } from "react";
import { api, json } from "../api";
import type { CaptureRecord } from "../types";

export function BaselineForm({
  bridgeId,
  history,
  onSaved,
}: {
  bridgeId: string;
  history: CaptureRecord[];
  onSaved: () => Promise<unknown>;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [token, setToken] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const candidates = history.filter(
    (row) =>
      row.result?.estimate?.outcome === "MEASURED" &&
      row.capture.temperature_c !== null,
  );
  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await api(`/bridges/${bridgeId}/baseline`, {
        method: "POST",
        headers: { Authorization: "Bearer " + token },
        body: json({ capture_ids: selected, confirmed_healthy: confirmed }),
      });
      setMessage(
        "Healthy baseline saved. It applies to subsequent measurements within its observed temperature range.",
      );
      setToken("");
      await onSaved();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Baseline could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="baseline-form" key={bridgeId}>
      <summary>Designate a healthy reference baseline</summary>
      <p>
        Choose distinct recordings whose healthy condition you have
        independently confirmed. A measured frequency alone does not establish
        health. Include temperature for every capture; repeated files cannot
        count as separate observations.
      </p>
      <fieldset>
        <legend>Eligible measured captures</legend>
        {candidates.length ? (
          candidates.map((row) => (
            <label key={row.capture.id} className="check">
              <input
                type="checkbox"
                checked={selected.includes(row.capture.id)}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, row.capture.id]
                      : selected.filter((id) => id !== row.capture.id),
                  )
                }
              />
              {row.capture.id} · {row.capture.temperature_c} °C ·{" "}
              {row.result?.estimate?.spectrum?.peak_hz.toFixed(3)} Hz
            </label>
          ))
        ) : (
          <p>
            No eligible captures yet. Record independent trials and include
            temperature.
          </p>
        )}
      </fieldset>
      <label className="check">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        I independently confirm that the selected captures represent a healthy
        reference condition.
      </label>
      <label>
        Reviewer token
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          autoComplete="off"
        />
      </label>
      <button
        disabled={busy || selected.length < 3 || !confirmed || !token}
        onClick={save}
      >
        Save healthy baseline
      </button>
      <p role="status">{message}</p>
    </details>
  );
}
