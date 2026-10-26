import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Baseline, Bridge } from "../types";

export function CurrentBaseline({ bridgeId }: { bridgeId: string }) {
  const baseline = useQuery({
    queryKey: ["baseline", bridgeId],
    queryFn: () => api<Baseline | null>(`/bridges/${bridgeId}/baseline`),
  });
  const value = baseline.data;
  return (
    <section
      className="panel current-baseline"
      aria-labelledby="baseline-title"
    >
      <div className="section-title">
        <h2 id="baseline-title">Healthy baseline</h2>
        <span className="mode-note">
          {baseline.isPending
            ? "Loading…"
            : value
              ? `${value.capture_ids.length} designated captures`
              : "Not designated"}
        </span>
      </div>
      {value ? (
        <dl className="facts">
          <div>
            <dt>Reference frequency</dt>
            <dd>{value.f0_hz.toFixed(3)} Hz</dd>
          </div>
          <div>
            <dt>Residual spread</dt>
            <dd>{value.residual_std_hz.toFixed(4)} Hz</dd>
          </div>
          <div>
            <dt>Valid temperatures</dt>
            <dd>
              {value.temperature_min_c.toFixed(1)} –{" "}
              {value.temperature_max_c.toFixed(1)} °C
            </dd>
          </div>
          <div>
            <dt>Temperature coefficient</dt>
            <dd>{value.alpha_per_c.toFixed(5)} per °C</dd>
          </div>
        </dl>
      ) : (
        <p className="help">
          {baseline.isPending
            ? "Loading baseline…"
            : "New measurements stay insufficient evidence until healthy captures are designated below."}
        </p>
      )}
    </section>
  );
}

export function DeleteBridge({
  bridge,
  onStart,
  onDeleted,
}: {
  bridge: Bridge;
  onStart: () => void;
  onDeleted: (message: string) => void;
}) {
  const [token, setToken] = useState("");
  const [typed, setTyped] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  if (bridge.synthetic) return null;
  async function remove() {
    setBusy(true);
    setMessage("");
    onStart();
    try {
      const result = await api<{ captures_deleted: number }>(
        `/bridges/${bridge.bridge.id}`,
        { method: "DELETE", headers: { Authorization: "Bearer " + token } },
      );
      onDeleted(
        `Deleted ${bridge.bridge.name} with ${result.captures_deleted} capture${result.captures_deleted === 1 ? "" : "s"}, their videos and evidence.`,
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "The bridge could not be deleted.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="baseline-form danger-zone">
      <summary>Delete this bridge</summary>
      <p>
        Permanently removes {bridge.bridge.name}, its captures, uploaded videos,
        evidence files, baseline and inspection requests. This cannot be undone.
      </p>
      <label>
        Type the bridge name to confirm
        <input
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          autoComplete="off"
        />
      </label>
      <label>
        Admin token
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          autoComplete="off"
        />
      </label>
      <button
        className="ghost danger"
        disabled={busy || !token || typed !== bridge.bridge.name}
        onClick={remove}
      >
        Delete bridge permanently
      </button>
      <p role="status">{message}</p>
    </details>
  );
}
