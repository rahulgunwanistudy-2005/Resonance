import { useMemo, useState } from "react";
import type { DeskResult } from "../types";

// eval/desk.py labels each trial by its filename prefix: healthy_1.mp4 -> "healthy".
const STATES = [
  {
    key: "healthy",
    label: "Healthy",
    how: "Reference run, clamps tight, no added mass",
    color: "#3DE0D0",
  },
  {
    key: "loosened",
    label: "Clamps loosened",
    how: "Quarter turn off each clamp",
    color: "#FFB454",
  },
  {
    key: "mass",
    label: "Added mass",
    how: "Known weight at midspan",
    color: "#B98CFF",
  },
  {
    key: "cut",
    label: "Saw cut",
    how: "Partial cut in one member",
    color: "#FF6B6B",
  },
] as const;
type StateKey = (typeof STATES)[number]["key"];
const mean = (values: number[]) =>
  values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;

export function Desk({
  data,
  target,
}: {
  data: DeskResult | undefined;
  target: number | undefined;
}) {
  const [step, setStep] = useState<StateKey | "compare">("healthy");
  const groups = useMemo(() => {
    const rows = data?.captures ?? [];
    const byState = (key: string) => rows.filter((row) => row.state === key);
    const summary = (key: string) => {
      const trials = byState(key);
      return {
        trials,
        video: mean(
          trials.flatMap((t) => (t.video_hz == null ? [] : [t.video_hz])),
        ),
        accelerometer: mean(trials.map((t) => t.accelerometer_hz)),
      };
    };
    const known = new Set<string>(STATES.map((s) => s.key));
    const extra = [...new Set(rows.map((r) => r.state))].filter(
      (s) => !known.has(s),
    );
    return {
      healthy: summary("healthy"),
      of: summary,
      extra,
    };
  }, [data]);
  const recorded = data?.captures.length ?? 0;
  const healthy = groups.healthy.video;
  const shift = (value: number | null) =>
    value != null && healthy != null && value !== healthy
      ? ((value - healthy) / healthy) * 100
      : null;
  const current =
    step === "compare" ? null : STATES.find((s) => s.key === step)!;
  const after = current ? groups.of(current.key) : null;
  const afterShift = after ? shift(after.video) : null;
  const passing = (data?.captures ?? []).filter(
    (row) =>
      target != null &&
      row.frequency_error_percent != null &&
      row.frequency_error_percent <= target,
  ).length;
  const scaleMax = Math.max(
    0,
    ...STATES.map((s) => groups.of(s.key).video ?? 0),
  );

  return (
    <div className="desk">
      <div className="page-heading">
        <div>
          <p className="context">Ground-truth experiment</p>
          <h1 className="display">Desk Bridge Experiment</h1>
          <p className="lede">See how damage changes the bridge's voice.</p>
        </div>
        <span className="local-mode">
          {recorded
            ? `${recorded} recorded trial${recorded === 1 ? "" : "s"}`
            : "Ready for recordings"}
        </span>
      </div>

      <div className="steps" role="group" aria-label="Experiment state">
        {STATES.map((s, i) => (
          <button
            key={s.key}
            className="step"
            aria-pressed={step === s.key}
            style={step === s.key ? { borderColor: s.color } : undefined}
            onClick={() => setStep(s.key)}
          >
            <span>{i + 1}</span>
            {s.label}
          </button>
        ))}
        <button
          className="step"
          aria-pressed={step === "compare"}
          onClick={() => setStep("compare")}
        >
          <span>{STATES.length + 1}</span>Compare
        </button>
      </div>

      <section className="desk-model" aria-label="Desk rig illustration">
        <DeskRig state={step} />
      </section>

      {step === "compare" ? (
        <section className="panel" aria-labelledby="compare-title">
          <h2 id="compare-title">Compare video frequency by state</h2>
          {recorded ? (
            <div className="bars">
              {STATES.map((s) => {
                const g = groups.of(s.key);
                const delta = shift(g.video);
                return (
                  <div className="bar-row" key={s.key}>
                    <span>{s.label}</span>
                    <div className="bar-track">
                      <div
                        className="bar"
                        style={{
                          background: s.color,
                          width:
                            g.video != null && scaleMax
                              ? `${(g.video / scaleMax) * 100}%`
                              : "0",
                        }}
                      />
                    </div>
                    <span style={{ color: s.color }}>
                      {g.video != null
                        ? `${g.video.toFixed(2)} Hz` +
                          (delta != null
                            ? ` · ${delta < 0 ? "−" : "+"}${Math.abs(delta).toFixed(1)}%`
                            : "")
                        : "No data"}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="placeholder">
              Record at least the healthy state and one changed state to
              compare.
            </p>
          )}
        </section>
      ) : (
        <div className="panel-row">
          <section className="panel" aria-labelledby="desk-before">
            <h3 id="desk-before">Before (healthy)</h3>
            <Reading
              video={groups.healthy.video}
              accelerometer={groups.healthy.accelerometer}
              trials={groups.healthy.trials.length}
              color="#3DE0D0"
            />
          </section>
          <section className="panel" aria-labelledby="desk-after">
            <h3 id="desk-after">After ({current!.label.toLowerCase()})</h3>
            {current!.key === "healthy" ? (
              <p className="placeholder">
                Choose a changed state to compare it with the healthy run.
              </p>
            ) : (
              <Reading
                video={after!.video}
                accelerometer={after!.accelerometer}
                trials={after!.trials.length}
                color={current!.color}
                shift={afterShift}
              />
            )}
          </section>
          <section className="panel" aria-labelledby="desk-record">
            <h3 id="desk-record">Record this state</h3>
            <p className="help">{current!.how}.</p>
            <p className="help">
              Save the pair as <code>{current!.key}_1.mp4</code> and{" "}
              <code>{current!.key}_1.csv</code> in <code>data/desk</code>. Add{" "}
              <code>_2</code>, <code>_3</code> for repeat trials.
            </p>
          </section>
        </div>
      )}

      <section className="panel desk-table" aria-labelledby="truth-title">
        <div className="section-title">
          <h2 id="truth-title" className="display small">
            Video against the accelerometer
          </h2>
          <span className="mode-note">
            {recorded
              ? "From eval/results/desk.json"
              : "Rows fill in after the desk evaluator runs"}
          </span>
        </div>
        <div className="table-scroll" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>State</th>
                <th>Trial</th>
                <th>Accelerometer (Hz)</th>
                <th>Video (Hz)</th>
                <th>Error</th>
                <th>Shift vs healthy</th>
              </tr>
            </thead>
            <tbody>
              {recorded
                ? [...STATES.map((s) => s.key), ...groups.extra].flatMap(
                    (key) =>
                      groups.of(key).trials.map((row) => {
                        const delta = shift(row.video_hz);
                        return (
                          <tr key={row.capture_id}>
                            <th>
                              {STATES.find((s) => s.key === key)?.label ?? key}
                            </th>
                            <td>{row.capture_id}</td>
                            <td>{row.accelerometer_hz.toFixed(3)}</td>
                            <td>
                              {row.video_hz != null
                                ? row.video_hz.toFixed(3)
                                : row.outcome.replaceAll("_", " ")}
                            </td>
                            <td>
                              {row.frequency_error_percent != null
                                ? row.frequency_error_percent.toFixed(2) + "%"
                                : "–"}
                            </td>
                            <td>
                              {key === "healthy"
                                ? "Reference"
                                : delta != null
                                  ? `${delta < 0 ? "−" : "+"}${Math.abs(delta).toFixed(1)}%`
                                  : "–"}
                            </td>
                          </tr>
                        );
                      }),
                  )
                : STATES.map((s) => (
                    <tr key={s.key}>
                      <th>
                        {s.label}
                        <div className="sub">{s.how}</div>
                      </th>
                      <td className="muted">No data</td>
                      <td className="muted">–</td>
                      <td className="muted">–</td>
                      <td className="muted">–</td>
                      <td className="muted">
                        {s.key === "healthy" ? "Reference" : "–"}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
        {recorded > 0 && target != null && (
          <p className="help">
            {passing} of {recorded} trials fall within the{" "}
            {target.toLocaleString()}% frequency-error target used by the
            synthetic evaluation.
          </p>
        )}
        <div className="desk-notes">
          <div>
            <h3>Rig</h3>
            <p>
              A steel ruler or aluminium beam clamped at both ends. Phone A is
              taped to the beam running phyphox as ground truth. Phone B films
              in slow motion from a tripod, with the acquisition rate confirmed.
            </p>
          </div>
          <div>
            <h3>Honest limits</h3>
            <p>
              <strong>Frame rate:</strong> at least about twice the mode
              frequency. <strong>Amplitude:</strong> stiff short spans barely
              move. <strong>Scope:</strong> triage between inspections, not a
              replacement. A desk rig is not a bridge.
            </p>
            {data?.limitations?.length ? (
              <ul className="limits">
                {data.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      </section>

      <div className="evidence-grid">
        <section className="panel" aria-labelledby="run-title">
          <h2 id="run-title">Run the experiment</h2>
          <ol className="run-steps">
            <li>
              Record each state as a video and a phyphox accelerometer export
              with matching names, for example <code>healthy_1.mp4</code> and{" "}
              <code>healthy_1.csv</code>.
            </li>
            <li>
              Give each CSV the columns <code>time_seconds</code> and{" "}
              <code>acceleration_m_s2</code>, with regular timestamps.
            </li>
            <li>
              Put the pairs in <code>data/desk</code>, and the template from
              this page in the project folder.
            </li>
            <li>
              Run{" "}
              <code>
                .venv/bin/python -m eval.desk --root data/desk --template
                desk-capture-template.json
              </code>
              , then reload this page.
            </li>
          </ol>
        </section>
        <TemplateBuilder />
      </div>
    </div>
  );
}

function Reading({
  video,
  accelerometer,
  trials,
  color,
  shift,
}: {
  video: number | null;
  accelerometer: number | null;
  trials: number;
  color: string;
  shift?: number | null;
}) {
  if (!trials) return <p className="placeholder">No trials recorded for this state.</p>;
  return (
    <>
      <p className="reading" style={{ color }}>
        {video != null ? video.toFixed(3) : "No reading"} <small>Hz</small>
        {shift != null && (
          <span className="delta">
            {shift < 0 ? "▼" : "▲"} {Math.abs(shift).toFixed(1)}% vs healthy
          </span>
        )}
      </p>
      <p className="reading-label">
        Video mean of {trials} trial{trials === 1 ? "" : "s"} · accelerometer{" "}
        {accelerometer != null ? accelerometer.toFixed(3) : "–"} Hz
      </p>
    </>
  );
}

function TemplateBuilder() {
  const [fps, setFps] = useState("240"),
    [low, setLow] = useState("1"),
    [high, setHigh] = useState("40"),
    [temperature, setTemperature] = useState(""),
    [roi, setRoi] = useState({ x: 0, y: 0, width: 128, height: 64 });
  const template = {
    id: "template",
    bridge_id: "desk-rig",
    path: "data/desk/template.mp4",
    band: { low_hz: Number(low), high_hz: Number(high) },
    rois: [{ id: "deck", ...roi }],
    calibration: null,
    temperature_c: temperature === "" ? null : Number(temperature),
    acquisition_fps: Number(fps),
    acquisition_fps_verified: true,
  };
  const href =
    "data:application/json;charset=utf-8," +
    encodeURIComponent(JSON.stringify(template, null, 2) + "\n");
  return (
    <section className="panel form-panel" aria-labelledby="template-title">
      <h2 id="template-title">Capture template</h2>
      <p className="help">
        The evaluator applies these settings to every desk video. Read the
        region from a frame of your own recording, in video pixel coordinates.
      </p>
      <div className="field-pair">
        <label>
          Acquisition frame rate
          <input
            type="number"
            min="1"
            max="1000"
            value={fps}
            onChange={(e) => setFps(e.target.value)}
          />
        </label>
        <label>
          Temperature (°C, optional)
          <input
            type="number"
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
          />
        </label>
        <label>
          Lower band (Hz)
          <input
            type="number"
            min="0.1"
            step="0.1"
            value={low}
            onChange={(e) => setLow(e.target.value)}
          />
        </label>
        <label>
          Upper band (Hz)
          <input
            type="number"
            min="0.2"
            step="0.1"
            value={high}
            onChange={(e) => setHigh(e.target.value)}
          />
        </label>
      </div>
      <fieldset>
        <legend>Beam region</legend>
        <div className="field-pair">
          {(["x", "y", "width", "height"] as const).map((key) => (
            <label key={key}>
              Region {key}
              <input
                type="number"
                min={key === "width" || key === "height" ? 16 : 0}
                value={roi[key]}
                onChange={(e) =>
                  setRoi({ ...roi, [key]: Number(e.target.value) })
                }
              />
            </label>
          ))}
        </div>
      </fieldset>
      <a className="primary" href={href} download="desk-capture-template.json">
        Download template
      </a>
      <p className="help">
        Only confirm the frame rate you set on the camera itself; slow-motion
        playback metadata can misreport it.
      </p>
    </section>
  );
}

function DeskRig({ state }: { state: StateKey | "compare" }) {
  let truss = "";
  let nodes = "";
  for (let k = 0; k < 8; k++) {
    const x = 120 + 95 * k;
    truss += `M${x} 190 L${x + 47.5} 120 L${x + 95} 190 `;
  }
  for (let k = 0; k <= 8; k++) nodes += `M${120 + 95 * k} 190 h0.1 `;
  for (let k = 0; k < 8; k++) nodes += `M${167.5 + 95 * k} 120 h0.1 `;
  const mass = state === "mass";
  const cut = state === "cut";
  const loose = state === "loosened";
  return (
    <>
      <svg
        viewBox="0 0 1000 300"
        role="img"
        aria-label={
          "Truss model beam clamped at both ends on a desk" +
          (mass
            ? ", with a mass at midspan"
            : cut
              ? ", with one member partly cut"
              : loose
                ? ", with the end clamps loosened"
                : "")
        }
      >
        <defs>
          <linearGradient id="desk-top" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4A3426" />
            <stop offset="1" stopColor="#1D140F" />
          </linearGradient>
          <linearGradient id="desk-wall" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0E1530" />
            <stop offset="1" stopColor="#1A2144" />
          </linearGradient>
        </defs>
        <rect width="1000" height="224" fill="url(#desk-wall)" />
        <rect y="224" width="1000" height="76" fill="url(#desk-top)" />
        <line x1="0" y1="224" x2="1000" y2="224" stroke="#6B4C37" />
        <ellipse cx="500" cy="232" rx="400" ry="9" fill="#000" opacity="0.35" />
        {[92, 874].map((x) => (
          <g key={x}>
            <rect
              x={x}
              y="96"
              width="34"
              height="124"
              rx="4"
              fill="#2A3350"
              stroke={loose ? "#FFB454" : "#55628F"}
            />
            <rect
              x={x - 10}
              y="216"
              width="56"
              height="12"
              rx="3"
              fill="#1A2140"
              stroke="#55628F"
            />
          </g>
        ))}
        <path
          d={truss}
          fill="none"
          stroke="#D3DCEB"
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <path
          d="M120 120 H880 M120 190 H880"
          fill="none"
          stroke="#D3DCEB"
          strokeWidth="3.5"
          strokeLinecap="round"
        />
        <path
          d={nodes}
          fill="none"
          stroke="#9FB0CC"
          strokeWidth="7"
          strokeLinecap="round"
        />
        {mass && (
          <g>
            <rect
              x="446"
              y="84"
              width="108"
              height="36"
              rx="3"
              fill="#7F8FB0"
              stroke="#C5CFE2"
            />
            <text
              x="500"
              y="108"
              textAnchor="middle"
              fontSize="14"
              fill="#0B1022"
              fontWeight="600"
            >
              + mass
            </text>
          </g>
        )}
        {cut && (
          <g>
            <path
              d="M405 190 L452.5 120"
              stroke="#FF6B6B"
              strokeWidth="16"
              strokeLinecap="round"
              opacity="0.28"
            />
            <path
              d="M405 190 L452.5 120"
              stroke="#FF6B6B"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="26 8"
            />
          </g>
        )}
      </svg>
      {(cut || mass || loose) && (
        <p className={"scribble desk-note " + state} aria-hidden="true">
          {cut
            ? "saw cut (member damaged)"
            : mass
              ? "known weight at midspan"
              : "clamps a quarter turn loose"}
        </p>
      )}
    </>
  );
}
