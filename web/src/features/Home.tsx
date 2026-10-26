import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { BridgeScene } from "../components/BridgeScene";
import { Arrow, PlayGlyph, Spark } from "../components/Marks";
import type { CaptureRecord } from "../types";
export function Home({ onOpen }: { onOpen: (capture: string) => void }) {
  const [changed, setChanged] = useState(false);
  const [deflection, setDeflection] = useState(0);
  const video = useRef<HTMLVideoElement>(null);
  const animation = useRef<number>(0);
  useEffect(() => () => cancelAnimationFrame(animation.current), []);
  const history = useQuery({
    queryKey: ["history", "demo-bridge"],
    queryFn: () => api<CaptureRecord[]>("/bridges/demo-bridge/history"),
  });
  const reference = history.data?.find(
    (row) => row.capture.id === "demo-capture-1",
  );
  const altered = history.data?.find(
    (row) => row.capture.id === "demo-capture-4",
  );
  const record = changed ? altered : reference;
  const estimate = record?.result?.estimate;
  const before = reference?.result?.estimate;
  const after = altered?.result?.estimate;
  const shift =
    before?.spectrum && after?.spectrum
      ? after.spectrum.peak_hz - before.spectrum.peak_hz
      : null;
  function animate() {
    const current = video.current;
    const series = estimate?.selected;
    if (current && series) {
      const index = Math.min(
        series.displacement_px.length - 1,
        Math.round(current.currentTime * series.fps),
      );
      setDeflection(
        current.currentTime <=
          series.time_seconds[series.time_seconds.length - 1]
          ? series.displacement_px[index] * 12
          : 0,
      );
      if (!current.paused) animation.current = requestAnimationFrame(animate);
    }
  }
  function pick(next: boolean) {
    cancelAnimationFrame(animation.current);
    setChanged(next);
    setDeflection(0);
  }
  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-scene">
          <BridgeScene
            mood="dusk"
            label="Illustrated suspension bridge at dusk with a wave ribbon along the deck"
          />
        </div>
        <div className="hero-body">
          <div className="hero-copy">
            <p className="eyebrow">
              Cameras listen.
              <br />
              Bridges speak.
            </p>
            <h1 id="hero-title">
              Every bridge
              <br />
              has a <em>heartbeat.</em>
            </h1>
            <p className="hero-lede">
              Resonance turns an ordinary recording into vibration evidence, so
              a persistent change in how a structure moves can be questioned
              while an engineer stays in control.
            </p>
            <div className="hero-actions">
              <a className="primary" href="#/measure">
                Measure a video
                <Arrow />
              </a>
              <button
                className="play-link"
                onClick={() => record && onOpen(record.capture.id)}
                disabled={!record}
              >
                <span className="play-ring">
                  <PlayGlyph />
                </span>
                Open demonstration
              </button>
            </div>
          </div>
          <div className="hero-aside">
            <p className="scribble" aria-hidden="true">
              The bridge
              <br />
              is breathing.
            </p>
            <div className="dial">
              <svg viewBox="0 0 110 36" aria-hidden="true">
                <path d="M2 18 C12 18 14 4 24 4 S36 32 46 32 S58 4 68 4 S80 32 90 32 S98 18 108 18" />
              </svg>
              <strong>
                {before?.spectrum ? (
                  <>
                    {before.spectrum.peak_hz.toFixed(2)} <small>Hz</small>
                  </>
                ) : (
                  "Not run"
                )}
              </strong>
              <span>Demo reference frequency</span>
            </div>
          </div>
        </div>
        <ul className="hero-principles">
          <li>
            <strong>Evidence before a verdict</strong>
            <span>
              Weak texture, uncertain timing or no baseline yield insufficient
              evidence.
            </span>
          </li>
          <li>
            <strong>A plan that responds</strong>
            <span>
              The agent changes regions, windows and methods when the visual
              evidence is weak.
            </span>
          </li>
          <li>
            <strong>Review stays human</strong>
            <span>
              A confirmed change requests inspection review, never a safety
              verdict.
            </span>
          </li>
          <li>
            <strong>Every camera</strong>
            <span>A stethoscope for the structure it can see.</span>
          </li>
        </ul>
      </section>

      <section className="demo" aria-labelledby="demo-title">
        <div className="demo-heading">
          <h2 id="demo-title" className="display">
            Hear a change in the beam's voice
          </h2>
          <p>
            Two generated captures of the same beam: a reference, and one with
            its stiffness altered. Not evidence of real bridge damage.
          </p>
        </div>
        <div className="steps" role="group" aria-label="Demonstration capture">
          <button
            className="step"
            aria-pressed={!changed}
            onClick={() => pick(false)}
          >
            <span>1</span>Reference capture
          </button>
          <button
            className="step changed"
            aria-pressed={changed}
            onClick={() => pick(true)}
          >
            <span>2</span>Changed frequency
          </button>
        </div>
        <div className={"demo-stage" + (record ? "" : " empty")}>
          {record ? (
            <>
              <video
                ref={video}
                key={record.capture.id}
                controls
                preload="auto"
                src={`/api/captures/${record.capture.id}/video`}
                onPlay={animate}
                onPause={() => cancelAnimationFrame(animation.current)}
                aria-label="Generated beam reference and changed-frequency video"
              />
              <svg viewBox="0 0 400 260" aria-hidden="true">
                <path
                  d={`M34 132 Q200 ${132 + deflection} 366 132`}
                  fill="none"
                  strokeWidth="2"
                />
              </svg>
            </>
          ) : (
            <>
              <BridgeScene mood="night" ribbon={false} />
              <p className="stage-empty" role="status">
                {history.isPending
                  ? "Loading the generated demonstration…"
                  : "The generated demonstration has not been seeded yet."}
              </p>
            </>
          )}
        </div>
        <div className="panel-row">
          <section className="panel" aria-labelledby="before-title">
            <h3 id="before-title">Before (reference)</h3>
            <p className="reading">
              {before?.spectrum ? (
                <>
                  {before.spectrum.peak_hz.toFixed(3)} <small>Hz</small>
                </>
              ) : (
                "Not run"
              )}
            </p>
            {before?.selected && (
              <Spark
                values={before.selected.displacement_px}
                className="teal"
              />
            )}
          </section>
          <section className="panel" aria-labelledby="after-title">
            <h3 id="after-title">After (changed)</h3>
            {after?.spectrum ? (
              <>
                <p className="reading coral">
                  {after.spectrum.peak_hz.toFixed(3)} <small>Hz</small>
                  {shift !== null && before?.spectrum && (
                    <span className="delta">
                      {shift < 0 ? "▼" : "▲"} {Math.abs(shift).toFixed(3)} Hz ·{" "}
                      {Math.abs(
                        (shift / before.spectrum.peak_hz) * 100,
                      ).toFixed(1)}
                      %
                    </span>
                  )}
                </p>
                {after.selected && (
                  <Spark
                    values={after.selected.displacement_px}
                    className="coral"
                  />
                )}
              </>
            ) : (
              <p className="placeholder">Run the changed capture to compare.</p>
            )}
          </section>
          <section className="panel" aria-labelledby="listen-title">
            <h3 id="listen-title">Listen</h3>
            {record?.artifacts.includes("motion.wav") && (
              <label className="listen-label">
                Listen to measured motion, time-compressed and looped
                <audio
                  key={record.capture.id}
                  controls
                  preload="none"
                  src={`/api/captures/${record.capture.id}/artifacts/motion.wav`}
                />
              </label>
            )}
            <p className="help">
              The deflection overlay is exaggerated and stops at the measured
              window. The tone comes from measured displacement, played faster
              and looped. A lower frequency sounds flat. Amplitude remains
              experimental.
            </p>
          </section>
        </div>
      </section>
    </>
  );
}
