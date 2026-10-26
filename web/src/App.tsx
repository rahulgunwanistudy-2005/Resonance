import { Home } from "./features/Home";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json } from "./api";
import type {
  Approval,
  Bridge,
  CaptureRecord,
  Evidence,
  Status,
} from "./types";
import { Chart } from "./components/Chart";
import { Timeline } from "./components/Timeline";
import { BaselineForm } from "./features/BaselineForm";
import { Upload } from "./features/Upload";
const routes = [
  ["home", "Overview"],
  ["console", "Bridge console"],
  ["measure", "Measure a video"],
  ["fleet", "Fleet"],
  ["agent", "Agent review"],
  ["bench", "Benchmarks"],
  ["methods", "Methods"],
];
const statusName = (status: string) =>
  ({
    NORMAL: "No change detected",
    WATCH: "Watch",
    ALERT: "Review requested",
    INSUFFICIENT_EVIDENCE: "Insufficient evidence",
  })[status] || status.replaceAll("_", " ");
function Badge({ status }: { status: string }) {
  return (
    <span className={`badge ${status.toLowerCase()}`}>
      {statusName(status)}
    </span>
  );
}
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
export default function App() {
  const client = useQueryClient();
  const [route, setRoute] = useState(location.hash.slice(2) || "home"),
    [bridgeId, setBridgeId] = useState("demo-bridge"),
    [captureId, setCaptureId] = useState("");
  useEffect(() => {
    const change = () => setRoute(location.hash.slice(2) || "home");
    addEventListener("hashchange", change);
    return () => removeEventListener("hashchange", change);
  }, []);
  const bridges = useQuery({
    queryKey: ["bridges"],
    queryFn: () => api<Bridge[]>("/bridges"),
  });
  const history = useQuery({
    queryKey: ["history", bridgeId],
    queryFn: () => api<CaptureRecord[]>(`/bridges/${bridgeId}/history`),
    refetchInterval: 2000,
  });
  useEffect(() => {
    const socket = new WebSocket(
      `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/live/${bridgeId}`,
    );
    socket.onmessage = () => {
      void client.invalidateQueries({ queryKey: ["history", bridgeId] });
      void client.invalidateQueries({ queryKey: ["capture"] });
      void client.invalidateQueries({ queryKey: ["approvals"] });
    };
    return () => socket.close();
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
    refetchInterval: 3000,
  });
  const evaluation = useQuery({
    queryKey: ["eval"],
    queryFn: () => api<Evidence>("/eval"),
  });
  const benches = useQuery({
    queryKey: ["bench"],
    queryFn: () => api<Evidence>("/bench"),
  });
  const record = captureId ? selected.data : history.data?.[0];
  const estimate = record?.result?.estimate;
  const decision = record?.result?.decision;
  const bridge = bridges.data?.find((item) => item.bridge.id === bridgeId);
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
  return (
    <>
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <header className="masthead">
        <a className="brand" href="#/home">
          <svg viewBox="0 0 40 28" aria-hidden="true">
            <path d="M2 19H38M8 19V26M32 19V26M8 19Q20 0 32 19M14 19V10M20 19V7M26 19V10" />
          </svg>
          Resonance
        </a>
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
        <span className="local-mode">Local workspace</span>
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
        ) : route === "fleet" ? (
          <>
            <div className="page-heading">
              <h1>Bridge fleet</h1>
              <a className="primary" href="#/measure">
                Measure a video
              </a>
            </div>
            <p className="intro">
              Each row links to its measurements, evidence and requested
              actions.
            </p>
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
              <h1>Agent review</h1>
              <span className="mode-note">Deterministic policy</span>
            </div>
            <p className="intro">
              The vision evidence changes the plan. Inspection notifications
              require your approval.
            </p>
            <div className="review-layout">
              <section>
                <h2>Inspection requests</h2>
                {approvals.data?.length ? (
                  approvals.data.map((item) => (
                    <article className="approval" key={item.id}>
                      <div className="section-title">
                        <h3>
                          {item.capture_id.startsWith("demo-")
                            ? "Synthetic demonstration"
                            : item.capture_id}
                        </h3>
                        <Badge
                          status={
                            item.status === "pending" ? "ALERT" : item.status
                          }
                        />
                      </div>
                      <p>
                        Confirmed frequency drop. Review the measurement and its
                        trace before taking action.
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
                            className="primary"
                            onClick={() => approve(item.id, true)}
                          >
                            Approve inspection request
                          </button>
                          <button
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
                        </>
                      )}
                    </article>
                  ))
                ) : (
                  <p>
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
            <h2>Current measurement trace</h2>
            {record?.result ? (
              <Timeline events={record.result.trace} />
            ) : (
              <p>
                Choose a measurement from the bridge console to inspect its
                trace.
              </p>
            )}
          </>
        ) : route === "methods" ? (
          <>
            <h1>Methods & evaluation</h1>
            <p className="intro">
              Measure the motion. Keep the uncertainty. Report the failures.
            </p>
            <div className="method-layout">
              <section>
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
                <a href="/api/eval">Read evaluation JSON</a>
              </aside>
            </div>
          </>
        ) : route === "bench" ? (
          <>
            <h1>Benchmarks</h1>
            <p className="intro">
              Measured operation and pipeline runs. Local measurements stay
              separate from COOL and cloud claims.
            </p>
            <Bench data={benches.data} />
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
                <h1>{bridge?.bridge.name || "Watch a bridge breathe"}</h1>
              </div>
              <a className="primary" href="#/measure">
                Measure a video
              </a>
            </div>
            <div className="console-topline">
              <div className="source-label">
                {record?.synthetic
                  ? "Generated synthetic video"
                  : "Video measurement"}
                {record && <span>Capture {record.capture.id}</span>}
              </div>
              {decision && <Badge status={decision.status} />}
            </div>
            <div className="instrument">
              <section className="video-panel">
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
                    <p>
                      {record
                        ? "Private recording. Derived evidence is available below."
                        : "Run the generated demo or upload a recording to begin."}
                    </p>
                    <a href="#/measure">Choose a video</a>
                  </div>
                )}
                <div className="video-caption">
                  <span>
                    {record?.synthetic
                      ? "Synthetic deck motion. No real bridge condition is inferred."
                      : "Private upload; raw video is retained temporarily."}
                  </span>
                  {record?.artifacts.includes("motion.wav") && (
                    <audio
                      controls
                      preload="none"
                      src={`/api/captures/${record.capture.id}/artifacts/motion.wav`}
                      aria-label="Listen to time-compressed and looped measured displacement"
                    />
                  )}
                </div>
              </section>
              <aside className="readout">
                <h2>Measurement evidence</h2>
                {estimate?.spectrum ? (
                  <>
                    <dl>
                      <div>
                        <dt>Dominant frequency</dt>
                        <dd>
                          {estimate.spectrum.peak_hz.toFixed(3)} <span>Hz</span>
                        </dd>
                      </div>
                      <div>
                        <dt>Frequency interval</dt>
                        <dd className="small-reading">
                          {estimate.ci_hz?.map((v) => v.toFixed(3)).join(" – ")}{" "}
                          Hz
                        </dd>
                      </div>
                      <div>
                        <dt>Extraction method</dt>
                        <dd className="small-reading">
                          {estimate.selected?.method.replaceAll("_", " ")}
                        </dd>
                      </div>
                      <div>
                        <dt>Camera stabilization</dt>
                        <dd className="small-reading">
                          {estimate.stabilization_applied
                            ? "Applied"
                            : "Not applied"}
                        </dd>
                      </div>
                    </dl>
                    <p className="next-action">{decision?.reason}</p>
                    {decision?.approval_id && (
                      <a className="primary" href="#/agent">
                        Review inspection request
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
                  <div role="status">
                    <p>
                      {record?.status === "failed"
                        ? record.error
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
                  </div>
                )}
              </aside>
            </div>
            {estimate?.selected && estimate.spectrum && (
              <div className="analysis-layout">
                <div>
                  <Chart
                    title="Deck displacement"
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
                  <Chart
                    title="Frequency spectrum"
                    x={estimate.spectrum.frequency_hz}
                    y={estimate.spectrum.psd_px2_per_hz}
                    xLabel="Frequency (Hz)"
                    yLabel="Power spectral density"
                  />
                </div>
                <section
                  className="trace-panel"
                  tabIndex={0}
                  aria-label="Agent sequence"
                >
                  <div className="section-title">
                    <h2>What the agent did</h2>
                    <span className="mode-note">Deterministic</span>
                  </div>
                  {record?.result && <Timeline events={record.result.trace} />}
                </section>
              </div>
            )}
            {record?.artifacts.includes("magnified.webm") && (
              <section className="magnification">
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
            <BaselineForm
              key={bridgeId}
              bridgeId={bridgeId}
              history={history.data || []}
              onSaved={() =>
                client.invalidateQueries({ queryKey: ["history", bridgeId] })
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
    </>
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
