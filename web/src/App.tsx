import { Home } from "./features/Home";
import { useEffect, useState, type KeyboardEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json } from "./api";
import type {
  Approval,
  Bridge,
  CaptureRecord,
  DeskResult,
  Evidence,
  Health,
} from "./types";
import { Chart } from "./components/Chart";
import { Timeline } from "./components/Timeline";
import { ModeShape } from "./components/ModeShape";
import { BridgeFigure } from "./components/bridge/BridgeFigure";
import {
  Arrow,
  Badge,
  PlayGlyph,
  Spark,
  Wordmark,
  statusName,
} from "./components/Marks";
import { BaselineForm } from "./features/BaselineForm";
import { Upload } from "./features/Upload";
import { Desk } from "./features/Desk";
import { CurrentBaseline, DeleteBridge } from "./features/BridgeManage";
const routes = [
  ["home", "Home"],
  ["console", "Live console"],
  ["measure", "Measure"],
  ["fleet", "Network"],
  ["desk", "Desk bridge"],
  ["agent", "Inspections"],
  ["bench", "Benchmarks"],
  ["methods", "Methods"],
];
const statusColor: Record<string, string> = {
  NORMAL: "#3DE0D0",
  WATCH: "#FFB454",
  ALERT: "#FF6B6B",
  INSUFFICIENT_EVIDENCE: "#A9B6CE",
};
const triggerName: Record<string, string> = {
  operator_upload: "Operator upload",
  heavy_vehicle_exit: "Heavy vehicle exit",
  motion_energy: "Motion energy trigger",
};
function metric(value: unknown, path: string): string {
  let current = value;
  for (const part of path.split(".")) {
    if (typeof current !== "object" || current === null) return "Not run";
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "number"
    ? current.toLocaleString(undefined, { maximumFractionDigits: 4 })
    : "Not run";
}
// Stable pseudo-random placement so each enrolled bridge keeps its spot on the map.
function place(id: string): [number, number] {
  let h = 2166136261;
  for (const ch of id) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  const a = ((h >>> 0) % 1000) / 1000;
  const b = (((h >>> 10) >>> 0) % 1000) / 1000;
  return [44 + a * 50, 14 + b * 70];
}
// Routes look like #/console?bridge=ID&capture=ID so a reload keeps the selection.
function readHash() {
  const [path, query = ""] = location.hash.slice(2).split("?");
  const params = new URLSearchParams(query);
  return {
    route: path || "home",
    bridge: params.get("bridge"),
    capture: params.get("capture"),
  };
}
export default function App() {
  const client = useQueryClient();
  const initial = readHash();
  const [route, setRoute] = useState(initial.route),
    [bridgeId, setBridgeId] = useState(initial.bridge || "demo-bridge"),
    [captureId, setCaptureId] = useState(initial.capture || ""),
    [tab, setTab] = useState(0),
    [notice, setNotice] = useState("");
  useEffect(() => {
    if (route !== "console") return;
    const params = new URLSearchParams({ bridge: bridgeId });
    if (captureId) params.set("capture", captureId);
    const next = "#/console?" + params.toString();
    if (location.hash !== next) window.history.replaceState(null, "", next);
  }, [route, bridgeId, captureId]);
  useEffect(() => {
    const change = () => {
      const next = readHash();
      setRoute(next.route);
      setNotice("");
      if (next.bridge) setBridgeId(next.bridge);
      if (next.capture) setCaptureId(next.capture);
    };
    addEventListener("hashchange", change);
    return () => removeEventListener("hashchange", change);
  }, []);
  // Each query loads only on the tabs that show it; the largest payloads
  // (evaluation evidence, capture history) are skipped everywhere else.
  const on = (...routes: string[]) => routes.includes(route);
  const bridges = useQuery({
    queryKey: ["bridges"],
    queryFn: () => api<Bridge[]>("/bridges"),
    enabled: on("console", "fleet"),
  });
  const history = useQuery({
    queryKey: ["history", bridgeId],
    queryFn: () => api<CaptureRecord[]>(`/bridges/${bridgeId}/history`),
    enabled: on("console", "agent"),
  });
  // The live socket pushes history changes; reconnect if the API restarts.
  useEffect(() => {
    let socket: WebSocket;
    let retry = 0;
    let stopped = false;
    const connect = () => {
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/live/${bridgeId}`,
      );
      socket.onmessage = () => {
        void client.invalidateQueries({ queryKey: ["history", bridgeId] });
        void client.invalidateQueries({ queryKey: ["capture"] });
        void client.invalidateQueries({ queryKey: ["approvals"] });
      };
      socket.onclose = () => {
        if (!stopped) retry = window.setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(retry);
      socket.close();
    };
  }, [bridgeId, client]);
  const selected = useQuery({
    queryKey: ["capture", captureId],
    queryFn: () => api<CaptureRecord>("/captures/" + captureId),
    enabled: !!captureId,
    refetchInterval: (q) =>
      ["awaiting_upload", "queued", "processing"].includes(
        q.state.data?.status || "",
      )
        ? 1000
        : false,
  });
  const approvals = useQuery({
    queryKey: ["approvals"],
    queryFn: () => api<Approval[]>("/approvals"),
    enabled: on("fleet", "agent"),
    refetchInterval: on("fleet", "agent") ? 3000 : false,
  });
  const evaluation = useQuery({
    queryKey: ["eval"],
    queryFn: () => api<Evidence>("/eval"),
    enabled: on("methods", "desk"),
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health"),
    refetchInterval: 15000,
  });
  const benches = useQuery({
    queryKey: ["bench"],
    queryFn: () => api<Evidence>("/bench"),
    enabled: on("bench"),
  });
  const record = captureId ? selected.data : history.data?.[0];
  const estimate = record?.result?.estimate;
  const decision = record?.result?.decision;
  const bridge = bridges.data?.find((item) => item.bridge.id === bridgeId);
  const tone = statusColor[decision?.status ?? "NORMAL"];
  const working = ["awaiting_upload", "queued", "processing"].includes(
    record?.status ?? "",
  );
  const pending = approvals.data?.filter((a) => a.status === "pending") ?? [];
  const [token, setToken] = useState(""),
    [reason, setReason] = useState(""),
    [message, setMessage] = useState("");
  async function approve(id: string, approved: boolean) {
    setMessage("");
    try {
      await api("/approvals/" + id, {
        method: "POST",
        headers: { Authorization: "Bearer " + token },
        body: json({ approved, reason }),
      });
      await client.invalidateQueries({ queryKey: ["approvals"] });
      setMessage(
        approved
          ? "Approved. The local worker will record a delivery receipt. No email is sent in local mode."
          : "Rejected. Your reason is retained with the evidence.",
      );
      setReason("");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Review could not be saved.");
    }
  }
  function choose(id: string) {
    setBridgeId(id);
    setCaptureId("");
    location.hash = "/console";
  }
  const signalTabs = [
    "Motion signal",
    "Frequency spectrum",
    ...(estimate?.fdd ? ["Mode shape"] : []),
  ];
  const view = tab < signalTabs.length ? tab : 0;
  const regions = estimate?.roi_estimates ?? [];
  function tabKeys(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const next =
      (view + (e.key === "ArrowRight" ? 1 : -1) + signalTabs.length) %
      signalTabs.length;
    setTab(next);
    document.getElementById("signal-tab-" + next)?.focus();
  }
  return (
    <div className={"shell route-" + route}>
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <header className="masthead">
        <Wordmark />
        <nav aria-label="Main navigation">
          {routes.map(([id, label]) => (
            <a
              key={id}
              className={route === id ? "active" : ""}
              aria-current={route === id ? "page" : undefined}
              href={"#/" + id}
            >
              {label}
            </a>
          ))}
        </nav>
        <span
          className="local-mode"
          title={
            health.data
              ? [
                  health.data.planner,
                  health.data.transport,
                  health.data.stabilization_ready
                    ? "stabilization ready"
                    : "stabilization unavailable",
                  health.data.vehicle_detection_ready
                    ? "vehicle detection ready"
                    : "motion-energy trigger only",
                ].join(" · ")
              : undefined
          }
        >
          {health.data?.cloud_deployed ? "Cloud workspace" : "Local workspace"}
          {health.isError && " · API offline"}
        </span>
      </header>
      <main id="main">
        {route === "home" ? (
          <Home
            onOpen={(id) => {
              setBridgeId("demo-bridge");
              setCaptureId(id);
              location.hash = "/console";
            }}
          />
        ) : route === "measure" ? (
          <Upload
            onComplete={(bridge, capture) => {
              setBridgeId(bridge);
              setCaptureId(capture);
              client.invalidateQueries({ queryKey: ["bridges"] });
              location.hash = "/console";
            }}
          />
        ) : route === "desk" ? (
          <Desk
            data={evaluation.data?.desk as DeskResult | undefined}
            target={
              (
                evaluation.data?.synthetic as
                  | { targets?: { frequency_error_percent?: number } }
                  | undefined
              )?.targets?.frequency_error_percent
            }
          />
        ) : route === "fleet" ? (
          <>
            <section className="network" aria-labelledby="network-title">
              <div className="network-map" aria-hidden="true">
                <div className="dots" />
                {bridges.data?.map((item) => {
                  const [x, y] = place(item.bridge.id);
                  return (
                    <span
                      key={item.bridge.id}
                      className={
                        "node" +
                        (item.synthetic ? " generated" : "") +
                        (item.sampling_multiplier > 1 ? " sampling" : "") +
                        (item.bridge.id === bridgeId ? " current" : "")
                      }
                      style={{ left: x + "%", top: y + "%" }}
                    />
                  );
                })}
              </div>
              <div className="network-copy">
                <h1 id="network-title" className="display">
                  A network
                  <br />
                  that listens.
                </h1>
                <p className="lede">
                  One camera at a time. Each enrolled bridge or experiment links
                  to its measurements, evidence and requested actions.
                </p>
                <dl className="tallies">
                  <div>
                    <dt>Enrolled</dt>
                    <dd>{bridges.data?.length ?? "–"}</dd>
                  </div>
                  <div>
                    <dt>Increased sampling</dt>
                    <dd className="amber">
                      {bridges.data?.filter((b) => b.sampling_multiplier > 1)
                        .length ?? "–"}
                    </dd>
                  </div>
                  <div>
                    <dt>Awaiting review</dt>
                    <dd className="coral">
                      {approvals.data ? pending.length : "–"}
                    </dd>
                  </div>
                </dl>
                <a className="primary" href="#/measure">
                  Measure a video
                  <Arrow />
                </a>
              </div>
              {bridge && (
                <article className="focus-card">
                  <div className="thumb">
                    <BridgeFigure />
                  </div>
                  <div>
                    <h2>{bridge.bridge.name}</h2>
                    <p>
                      {bridge.synthetic
                        ? "Generated demonstration"
                        : "Uploaded recording"}
                      {bridge.bridge.span_type !== "unknown" &&
                        ` · ${bridge.bridge.span_type.replace("_", " ")}`}
                      {bridge.bridge.span_length_m != null &&
                        ` · ${bridge.bridge.span_length_m} m span`}
                    </p>
                  </div>
                  <button
                    className="ghost"
                    onClick={() => choose(bridge.bridge.id)}
                  >
                    Open console
                    <Arrow />
                  </button>
                </article>
              )}
              <ul className="legend" aria-label="Map legend">
                <li className="uploaded">Uploaded recording</li>
                <li className="generated">Generated demonstration</li>
                <li className="sampling">Increased sampling</li>
              </ul>
            </section>
            <h2 className="section-heading">Bridge fleet</h2>
            <div className="table-scroll" tabIndex={0}>
              <table>
                <thead>
                  <tr>
                    <th>Bridge or experiment</th>
                    <th>Evidence source</th>
                    <th>Sampling policy</th>
                    <th>Open</th>
                  </tr>
                </thead>
                <tbody>
                  {bridges.data?.map((item) => (
                    <tr key={item.bridge.id}>
                      <td>{item.bridge.name}</td>
                      <td>
                        {item.synthetic
                          ? "Generated demonstration"
                          : "Uploaded recording"}
                      </td>
                      <td>
                        {item.sampling_multiplier > 1
                          ? "Increased sampling requested"
                          : "Standard sampling"}
                      </td>
                      <td>
                        <button
                          className="quiet"
                          onClick={() => choose(item.bridge.id)}
                        >
                          Open console
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : route === "agent" ? (
          <>
            <div className="page-heading">
              <div>
                <p className="context">Agent review</p>
                <h1 className="display">Inspections</h1>
              </div>
              <span className="mode-note">Deterministic policy</span>
            </div>
            <p className="intro">
              The vision evidence changes the plan. Inspection notifications
              require your approval.
            </p>
            <div className="review-layout">
              <section aria-labelledby="requests-title">
                <h2 id="requests-title">Inspection requests</h2>
                {approvals.data?.length ? (
                  approvals.data.map((item) => (
                    <article className="ticket" key={item.id}>
                      <div className="thumb">
                        <BridgeFigure />
                      </div>
                      <div className="ticket-body">
                        <Badge
                          status={
                            item.status === "pending" ? "ALERT" : item.status
                          }
                        />
                        <h3>
                          {item.capture_id.startsWith("demo-")
                            ? "Synthetic demonstration"
                            : item.capture_id}
                        </h3>
                        <p className="meta">
                          {item.bridge_id} ·{" "}
                          {new Date(item.created_at).toLocaleString()}
                        </p>
                        <p>
                          Confirmed frequency drop. Review the measurement and
                          its trace before taking action.
                        </p>
                        <button
                          className="quiet"
                          onClick={() => {
                            setBridgeId(item.bridge_id);
                            setCaptureId(item.capture_id);
                            location.hash = "/console";
                          }}
                        >
                          Review evidence
                        </button>
                        {item.status === "pending" ? (
                          <div className="approval-actions">
                            <button
                              disabled={!token || !reason.trim()}
                              className="primary warm"
                              onClick={() => approve(item.id, true)}
                            >
                              Approve inspection request
                            </button>
                            <button
                              className="ghost"
                              disabled={!token || !reason.trim()}
                              onClick={() => approve(item.id, false)}
                            >
                              Reject request
                            </button>
                          </div>
                        ) : (
                          <>
                            <p>{item.reason}</p>
                            <p className="help">
                              Delivery: {item.delivery.replaceAll("_", " ")}
                            </p>
                            {item.resolved_at && (
                              <p className="meta">
                                Resolved{" "}
                                {new Date(item.resolved_at).toLocaleString()}
                              </p>
                            )}
                          </>
                        )}
                      </div>
                    </article>
                  ))
                ) : (
                  <p className="empty-message">
                    No inspection requests yet. Run a measurement to see the
                    agent's next action.
                  </p>
                )}
              </section>
              <aside className="form-panel">
                <h2>Reviewer access</h2>
                <label>
                  Admin token
                  <input
                    type="password"
                    autoComplete="off"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                  />
                </label>
                <label>
                  Review reason
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    maxLength={1000}
                  />
                </label>
                <p className="help">
                  The token stays in this page's memory. It is never saved in
                  browser storage. The local token file is described in the
                  README.
                </p>
                <p role="status">{message}</p>
                <h3>Human control</h3>
                <p>
                  The worker cannot send an inspection notification until this
                  request is approved. Rejection keeps its reason. Local mode
                  records a receipt and sends no external messages.
                </p>
              </aside>
            </div>
            <section className="panel loop" aria-labelledby="trace-title">
              <h2 id="trace-title">Current measurement trace</h2>
              {record?.result ? (
                <Timeline events={record.result.trace} />
              ) : (
                <p>
                  Choose a measurement from the bridge console to inspect its
                  trace.
                </p>
              )}
            </section>
          </>
        ) : route === "methods" ? (
          <>
            <h1 className="display">Methods & evaluation</h1>
            <p className="intro">
              Measure the motion. Keep the uncertainty. Report the failures.
            </p>
            <div className="method-layout">
              <section className="panel">
                <h2>What is running</h2>
                <p>
                  OpenCV extracts sub-pixel displacement using phase correlation
                  and Riesz local phase. Welch spectra locate a dominant mode
                  inside the supplied physics band. A residual block bootstrap
                  estimates conditional frequency uncertainty. Multiple regions
                  support frequency-domain decomposition.
                </p>
                <p>
                  Background stabilization uses ALIKED, LightGlue, MAGSAC and
                  optical flow when configured. The local demonstration has a
                  fixed camera. Real handheld validation is still pending.
                </p>
                <h2>Observed synthetic results</h2>
                <table>
                  <tbody>
                    {[
                      ["Eligible comparisons", "eligible_experiments"],
                      ["Frequency target passes", "frequency_passes"],
                      ["Amplitude target passes", "amplitude_passes"],
                    ].map(([label, key]) => (
                      <tr key={key}>
                        <th>{label}</th>
                        <td>
                          {metric(evaluation.data?.synthetic, "summary." + key)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p>
                  Amplitude misses its target in many cases. Geometric
                  calibration does not remove estimator bias.
                </p>
                <h2>Agent replay</h2>
                <table>
                  <tbody>
                    {[
                      ["Replayed captures", "captures"],
                      ["Expected outcomes reached", "successes"],
                      ["Changed-plan retries", "retries"],
                      ["Approval requests", "approval_requests"],
                    ].map(([label, key]) => (
                      <tr key={key}>
                        <th>{label}</th>
                        <td>
                          {metric(evaluation.data?.agent, "summary." + key)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="help">
                  Sources: repository synthetic and agent evaluator JSON, served
                  by the evaluation endpoint.
                </p>
              </section>
              <aside className="form-panel">
                <h2>Before interpreting a result</h2>
                <ul>
                  <li>
                    Verify acquisition timing; playback metadata can
                    misrepresent slow motion.
                  </li>
                  <li>
                    Use textured, unobscured regions and a valid frequency
                    prior.
                  </li>
                  <li>
                    Keep camera motion, temperature and baseline coverage in the
                    assessment.
                  </li>
                  <li>
                    The bootstrap interval is conditional on a stationary mode
                    model.
                  </li>
                  <li>
                    A desk experiment is not a bridge. Field repeatability is
                    not ground-truth accuracy.
                  </li>
                </ul>
                <h3>Still awaiting evidence</h3>
                <p>
                  Desk recordings and accelerometer ground truth, real handheld
                  clips, AWS deployment and COOL benchmarks.
                </p>
                <a href="#/desk">Set up the desk experiment</a>
                <a href="/api/eval">Read evaluation JSON</a>
              </aside>
            </div>
            <EvalDetails data={evaluation.data} />
          </>
        ) : route === "bench" ? (
          <>
            <h1 className="display">Benchmarks</h1>
            <p className="intro">
              Measured operation and pipeline runs. Local measurements stay
              separate from COOL and cloud claims.
            </p>
            <Bench data={benches.data} />
            <BenchDetails data={benches.data} />
            <p>
              COOL Graviton and equal-vCPU cloud comparisons have not run. Cost
              and cloud capacity are unavailable until those runs are measured.
            </p>
            <a href="/api/bench">Read benchmark JSON</a>
          </>
        ) : (
          <>
            <div className="page-heading">
              <div>
                <p className="context">
                  Structural vibration / evidence console
                </p>
                <h1 className="display">
                  {bridge?.bridge.name || "Watch a bridge breathe"}
                </h1>
              </div>
              <div className="heading-actions">
                <label className="bridge-picker">
                  <span className="visually-hidden">Bridge</span>
                  <select
                    value={bridgeId}
                    onChange={(e) => {
                      setNotice("");
                      setBridgeId(e.target.value);
                      setCaptureId("");
                    }}
                  >
                    {bridges.data?.map((item) => (
                      <option key={item.bridge.id} value={item.bridge.id}>
                        {item.bridge.name}
                      </option>
                    ))}
                  </select>
                </label>
                <a className="primary" href="#/measure">
                  Measure a video
                </a>
              </div>
            </div>
            {notice && (
              <p role="status" className="notice">
                {notice}
              </p>
            )}
            <div className="instrument">
              <section className="stage" aria-label="Recording">
                {record?.synthetic ? (
                  <video
                    key={record.capture.id}
                    controls
                    preload="metadata"
                    src={`/api/captures/${record.capture.id}/video`}
                    aria-label="Generated desk-beam vibration video"
                  />
                ) : (
                  <div className="camera-empty">
                    <BridgeFigure truck />
                    <div>
                      <p>
                        {record
                          ? "Private recording. Derived evidence is available below."
                          : "Run the generated demo or upload a recording to begin."}
                      </p>
                      <a href="#/measure">Choose a video</a>
                    </div>
                  </div>
                )}
                <span className="chip">
                  <span className="dot" style={{ background: tone }} />
                  {record?.synthetic
                    ? "Generated synthetic video"
                    : "Video measurement"}
                </span>
                {record && (
                  <span className="chip right">
                    {triggerName[record.capture.trigger_source ?? ""] ??
                      "Capture"}{" "}
                    · {record.capture.id}
                  </span>
                )}
              </section>
              <aside className="readout" aria-labelledby="vitals-title">
                <div className="section-title">
                  <h2 id="vitals-title">Measurement evidence</h2>
                  {decision && <Badge status={decision.status} />}
                </div>
                {estimate?.spectrum ? (
                  <>
                    <div className="vital">
                      <span className="label">Dominant frequency</span>
                      <p className="big">
                        {estimate.spectrum.peak_hz.toFixed(3)} <span>Hz</span>
                      </p>
                      <span className="label">
                        Interval{" "}
                        {estimate.ci_hz?.map((v) => v.toFixed(3)).join(" – ")}{" "}
                        Hz
                      </span>
                      {estimate.selected && (
                        <Spark
                          values={estimate.selected.displacement_px}
                          width={260}
                          height={56}
                          className={decision?.status.toLowerCase()}
                        />
                      )}
                    </div>
                    <dl className="vital-grid">
                      <div>
                        <dt>Extraction method</dt>
                        <dd className="method">
                          {estimate.selected?.method.replaceAll("_", " ")}
                        </dd>
                      </div>
                      <div>
                        <dt>Camera stabilization</dt>
                        <dd>
                          {estimate.stabilization_applied
                            ? "Applied"
                            : "Not applied"}
                        </dd>
                      </div>
                      <div>
                        <dt>Signal to noise</dt>
                        <dd>{estimate.spectrum.snr_db.toFixed(1)} dB</dd>
                      </div>
                      <div>
                        <dt>Temperature</dt>
                        <dd>
                          {record?.capture.temperature_c ?? "Not recorded"}
                          {record?.capture.temperature_c != null && " °C"}
                        </dd>
                      </div>
                    </dl>
                    <p className="next-action">{decision?.reason}</p>
                    {estimate?.reasons.length ? (
                      <ul className="reasons" aria-label="Evidence notes">
                        {estimate.reasons.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : null}
                    {decision?.approval_id && (
                      <a className="primary warm" href="#/agent">
                        Review inspection request
                        <Arrow />
                      </a>
                    )}
                    <p className="help">
                      Conditional interval. Amplitude remains experimental. No
                      structural safety conclusion.
                    </p>
                    <small>
                      OpenCV {estimate.provenance.cv2_version};{" "}
                      {estimate.provenance.cool_verified
                        ? "COOL verified"
                        : "local runtime"}
                    </small>
                  </>
                ) : (
                  <div role="status" className="readout-empty">
                    {working && (
                      <span className="pulse" aria-hidden="true">
                        <span />
                        <span />
                        <span />
                      </span>
                    )}
                    <p>
                      {record?.status === "failed"
                        ? "Measurement failed"
                        : record
                          ? statusName(record.status)
                          : history.isPending
                            ? "Loading measurements…"
                            : "No measurement yet."}
                    </p>
                    {record?.result?.decision.reason && (
                      <p>{record.result.decision.reason}</p>
                    )}
                    {record?.error && <p role="alert">{record.error}</p>}
                    {estimate?.reasons.length ? (
                      <ul className="reasons" aria-label="Evidence notes">
                        {estimate.reasons.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                )}
              </aside>
            </div>
            {estimate?.selected && estimate.spectrum && (
              <div className="analysis-layout">
                <section className="panel signals">
                  <div
                    role="tablist"
                    aria-label="Signal views"
                    className="tabs"
                    onKeyDown={tabKeys}
                  >
                    {signalTabs.map((label, i) => (
                      <button
                        key={label}
                        id={"signal-tab-" + i}
                        role="tab"
                        aria-selected={view === i}
                        aria-controls="signal-panel"
                        tabIndex={view === i ? 0 : -1}
                        onClick={() => setTab(i)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div
                    id="signal-panel"
                    role="tabpanel"
                    aria-labelledby={"signal-tab-" + view}
                  >
                    {view === 2 && estimate.fdd ? (
                      <ModeShape
                        fdd={estimate.fdd}
                        rois={record?.capture.rois ?? []}
                        color={tone}
                      />
                    ) : view === 0 ? (
                      <Chart
                        title="Deck displacement"
                        color={tone}
                        x={estimate.selected.time_seconds}
                        y={
                          estimate.selected.displacement_mm ||
                          estimate.selected.displacement_px
                        }
                        xLabel="Time (s)"
                        yLabel={
                          estimate.selected.displacement_mm
                            ? "Displacement (mm, unvalidated amplitude)"
                            : "Displacement (pixels)"
                        }
                      />
                    ) : (
                      <Chart
                        title="Frequency spectrum"
                        color={tone}
                        x={estimate.spectrum.frequency_hz}
                        y={estimate.spectrum.psd_px2_per_hz}
                        xLabel="Frequency (Hz)"
                        yLabel="Power spectral density"
                      />
                    )}
                  </div>
                </section>
                <section
                  className="panel playing"
                  aria-labelledby="playing-title"
                >
                  <h2 id="playing-title">Now playing</h2>
                  <div className="tone-row">
                    <div className="tone-ring" style={{ borderColor: tone }}>
                      <svg viewBox="0 0 76 30" aria-hidden="true">
                        <path
                          d="M1 15 C8 15 9 3 16 3 S24 27 31 27 S40 3 47 3 S55 27 62 27 S68 15 75 15"
                          stroke={tone}
                        />
                      </svg>
                    </div>
                    <p className="big">
                      {estimate.spectrum.peak_hz.toFixed(2)} <span>Hz</span>
                    </p>
                  </div>
                  {record?.artifacts.includes("motion.wav") ? (
                    <audio
                      controls
                      preload="none"
                      src={`/api/captures/${record.capture.id}/artifacts/motion.wav`}
                      aria-label="Listen to time-compressed and looped measured displacement"
                    />
                  ) : (
                    <p className="placeholder">
                      <PlayGlyph /> No tone rendered for this capture.
                    </p>
                  )}
                  <p className="help">
                    Measured displacement, time-compressed into the audible
                    range and looped. A stiffness loss makes it sing flat.
                  </p>
                </section>
              </div>
            )}
            {regions.length > 1 && (
              <section
                className="panel regions"
                aria-labelledby="regions-title"
              >
                <h2 id="regions-title">Measured regions</h2>
                <div className="table-scroll" tabIndex={0}>
                  <table>
                    <thead>
                      <tr>
                        <th>Region</th>
                        <th>Method</th>
                        <th>Peak (Hz)</th>
                        <th>Signal to noise (dB)</th>
                        <th>Used for the reading</th>
                      </tr>
                    </thead>
                    <tbody>
                      {regions.map((item) => (
                        <tr key={item.series.roi_id + item.series.method}>
                          <th>{item.series.roi_id}</th>
                          <td>{item.series.method.replaceAll("_", " ")}</td>
                          <td>{item.spectrum.peak_hz.toFixed(3)}</td>
                          <td>{item.spectrum.snr_db.toFixed(1)}</td>
                          <td>
                            {estimate?.selected?.roi_id ===
                              item.series.roi_id &&
                            estimate.selected.method === item.series.method
                              ? "Selected"
                              : "–"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
            {record?.result && (
              <section className="panel loop" aria-labelledby="loop-title">
                <div className="section-title">
                  <h2 id="loop-title">What the agent did</h2>
                  {decision?.approval_id ? (
                    <a className="primary warm" href="#/agent">
                      Open inspection request
                      <Arrow />
                    </a>
                  ) : (
                    <span className="mode-note">Deterministic</span>
                  )}
                </div>
                <Timeline events={record.result.trace} />
              </section>
            )}
            {record?.artifacts.includes("magnified.webm") && (
              <section className="panel magnification">
                <h2>Magnified motion evidence</h2>
                <video
                  controls
                  preload="none"
                  src={`/api/captures/${record.capture.id}/artifacts/magnified.webm`}
                  aria-label="Magnified measured motion of the generated beam region"
                />
                <p className="help">
                  Generated input only. A temporal band-pass filters the
                  measured displacement; the crop is translated with exaggerated
                  gain. This rendering is an approximation, not a calibrated
                  deflection measurement.
                </p>
              </section>
            )}
            <CurrentBaseline bridgeId={bridgeId} />
            <BaselineForm
              key={bridgeId}
              bridgeId={bridgeId}
              history={history.data || []}
              onSaved={() =>
                Promise.all([
                  client.invalidateQueries({ queryKey: ["history", bridgeId] }),
                  client.invalidateQueries({
                    queryKey: ["baseline", bridgeId],
                  }),
                ])
              }
            />
            <section className="history">
              <div className="section-title">
                <h2>Capture history</h2>
                <button
                  className="quiet"
                  onClick={() =>
                    client.invalidateQueries({
                      queryKey: ["history", bridgeId],
                    })
                  }
                >
                  Refresh history
                </button>
              </div>
              <div className="table-scroll" tabIndex={0}>
                <table>
                  <thead>
                    <tr>
                      <th>Capture</th>
                      <th>Recorded</th>
                      <th>Outcome</th>
                      <th>Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.data?.map((item) => (
                      <tr key={item.capture.id}>
                        <td>
                          {item.synthetic
                            ? "Generated beam capture"
                            : item.capture.id.slice(0, 10)}
                        </td>
                        <td>{new Date(item.created_at).toLocaleString()}</td>
                        <td>
                          {item.result ? (
                            <Badge status={item.result.decision.status} />
                          ) : (
                            statusName(item.status)
                          )}
                        </td>
                        <td>
                          <button
                            className="quiet"
                            onClick={() => setCaptureId(item.capture.id)}
                          >
                            View measurement
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            {bridge && (
              <DeleteBridge
                key={bridge.bridge.id}
                bridge={bridge}
                onStart={() => setNotice("")}
                onDeleted={(text) => {
                  setNotice(text);
                  setBridgeId("demo-bridge");
                  setCaptureId("");
                  void client.invalidateQueries({ queryKey: ["bridges"] });
                  void client.invalidateQueries({ queryKey: ["approvals"] });
                }}
              />
            )}
            {(history.error || selected.error) && (
              <p role="alert" className="error">
                {history.error?.message || selected.error?.message}
              </p>
            )}
          </>
        )}
      </main>
      <footer>
        <strong>Triage support. Not structural certification.</strong>
        <span>Resonance does not replace professional inspection.</span>
        <a href="#/methods">Methods, evidence & limitations</a>
      </footer>
    </div>
  );
}
function Bench({ data }: { data: Evidence | undefined }) {
  const local = data?.local as
    | {
        provenance?: { machine: string; cv2_version: string };
        workloads?: {
          name: string;
          mean_ms: number;
          ci95_ms: number;
          repeats_ms: number[];
        }[];
      }
    | undefined;
  return local?.workloads ? (
    <>
      <p>
        Local {local.provenance?.machine} runtime, OpenCV{" "}
        {local.provenance?.cv2_version}. Timing intervals describe repeated runs
        on this machine.
      </p>
      <div className="table-scroll" tabIndex={0}>
        <table>
          <thead>
            <tr>
              <th>Workload</th>
              <th>Mean time (ms)</th>
              <th>Interval half-width (ms)</th>
              <th>Measured repeats</th>
            </tr>
          </thead>
          <tbody>
            {local.workloads.map((item) => (
              <tr key={item.name}>
                <th>{item.name}</th>
                <td>{item.mean_ms.toFixed(3)}</td>
                <td>{item.ci95_ms.toFixed(3)}</td>
                <td>{item.repeats_ms.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  ) : (
    <p className="empty-message">
      No benchmark run is available yet. Run the repository benchmark command to
      populate this table.
    </p>
  );
}

type Row = Record<string, unknown>;
const num = (value: unknown, digits = 3) =>
  typeof value === "number" ? value.toFixed(digits) : "Not run";
const rows = (value: unknown, key: string): Row[] => {
  const list = (value as Row | undefined)?.[key];
  return Array.isArray(list) ? (list as Row[]) : [];
};
const notes = (value: unknown, key: string): string[] => {
  const list = (value as Row | undefined)?.[key];
  return Array.isArray(list) ? list.map(String) : [];
};
function Limits({
  items,
  title = "Limitations",
}: {
  items: string[];
  title?: string;
}) {
  return items.length ? (
    <>
      <h3>{title}</h3>
      <ul className="limits">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </>
  ) : null;
}
function EvalDetails({ data }: { data: Evidence | undefined }) {
  const failures = data?.failures;
  const quality = data?.quality as Row | undefined;
  const shake = data?.stabilization as Row | undefined;
  return (
    <div className="evidence-grid">
      <section className="panel" aria-labelledby="failures-title">
        <h2 id="failures-title">Failure cases</h2>
        <p className="help">
          Each scenario should be refused with insufficient evidence rather than
          produce a reading.
        </p>
        <div className="table-scroll" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Outcome</th>
                <th>Refused as expected</th>
              </tr>
            </thead>
            <tbody>
              {rows(failures, "scenarios").map((row) => (
                <tr key={String(row.scenario)}>
                  <th>{String(row.scenario).replaceAll("_", " ")}</th>
                  <td>{String(row.outcome).replaceAll("_", " ")}</td>
                  <td>{row.refused_as_expected ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Limits items={notes(failures, "pending")} title="Not yet covered" />
      </section>
      <section className="panel" aria-labelledby="quality-title">
        <h2 id="quality-title">Quality gates</h2>
        <dl className="facts">
          <div>
            <dt>Tests run</dt>
            <dd>{metric(quality, "tests")}</dd>
          </div>
          <div>
            <dt>Test failures</dt>
            <dd>{metric(quality, "test_failures")}</dd>
          </div>
          <div>
            <dt>All gates passed</dt>
            <dd>{quality ? (quality.all_passed ? "Yes" : "No") : "Not run"}</dd>
          </div>
        </dl>
        <h2>Synthetic camera shake</h2>
        <dl className="facts">
          <div>
            <dt>Error without stabilization (px)</dt>
            <dd>{num(shake?.raw_rmse_px)}</dd>
          </div>
          <div>
            <dt>Error with stabilization (px)</dt>
            <dd>{num(shake?.stabilized_rmse_px)}</dd>
          </div>
          <div>
            <dt>Benefit observed</dt>
            <dd>
              {shake ? (shake.benefit_observed ? "Yes" : "No") : "Not run"}
            </dd>
          </div>
        </dl>
        <Limits items={notes(shake, "limitations")} />
        <Limits
          items={notes(data?.agent, "limitations")}
          title="Agent replay limits"
        />
      </section>
    </div>
  );
}
function BenchDetails({ data }: { data: Evidence | undefined }) {
  const pool = data?.roi_pool;
  const refresh = data?.stabilization_refresh;
  const profile = data?.profile as Row | undefined;
  const hot = rows(profile, "functions")
    .slice()
    .sort((a, b) => Number(b.cumulative_seconds) - Number(a.cumulative_seconds))
    .slice(0, 6);
  return (
    <div className="evidence-grid">
      <section className="panel" aria-labelledby="pool-title">
        <h2 id="pool-title">Parallel region workers</h2>
        <div className="table-scroll" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>Workers</th>
                <th>Mean time (s)</th>
                <th>Interval half-width (s)</th>
                <th>Repeats</th>
              </tr>
            </thead>
            <tbody>
              {rows(pool, "rows").map((row) => (
                <tr key={String(row.workers)}>
                  <th>{String(row.workers)}</th>
                  <td>{num(row.mean_seconds)}</td>
                  <td>{num(row.ci95_seconds)}</td>
                  <td>
                    {Array.isArray(row.repeats_seconds)
                      ? row.repeats_seconds.length
                      : "Not run"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h2>Stabilization refresh trade-off</h2>
        <div className="table-scroll" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>Refresh every (frames)</th>
                <th>Processing (frames/s)</th>
                <th>Residual error (px)</th>
              </tr>
            </thead>
            <tbody>
              {rows(refresh, "rows").map((row, i) => (
                <tr key={i}>
                  <th>
                    {String(
                      (row.configuration as Row | undefined)?.refresh_frames ??
                        "–",
                    )}
                  </th>
                  <td>{num(row.processing_fps)}</td>
                  <td>{num(row.stabilized_rmse_px)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Limits items={notes(refresh, "limitations")} />
      </section>
      <section className="panel" aria-labelledby="profile-title">
        <h2 id="profile-title">Where the time goes</h2>
        <p className="help">
          Cumulative time per function in one profiled pipeline run.
        </p>
        <div className="table-scroll" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>Function</th>
                <th>Calls</th>
                <th>Cumulative (s)</th>
              </tr>
            </thead>
            <tbody>
              {hot.map((row) => (
                <tr key={String(row.function)}>
                  <th className="code">{String(row.function)}</th>
                  <td>{String(row.calls)}</td>
                  <td>{num(row.cumulative_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Limits items={notes(data?.local, "limitations")} />
        <Limits
          items={notes(profile, "limitations")}
          title="Profiling limits"
        />
      </section>
    </div>
  );
}
