import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
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
  return (
    <section className="home">
      <div className="home-copy">
        <p className="context">Camera-based structural triage</p>
        <h1>Watch a structure breathe.</h1>
        <p className="intro">
          An ordinary recording becomes vibration evidence. Follow the motion,
          question a persistent change, and keep an engineer in control.
        </p>
        <div className="home-actions">
          <a className="primary" href="#/measure">
            Measure a video
          </a>
          <button
            onClick={() => record && onOpen(record.capture.id)}
            disabled={!record}
          >
            Open demonstration
          </button>
        </div>
        <p className="privacy">
          The scene below is generated. It demonstrates the working measurement
          path; it is not evidence of real bridge damage.
        </p>
      </div>
      <div className="home-instrument">
        <div className="home-video">
          <video
            ref={video}
            key={record?.capture.id}
            controls
            preload="auto"
            src={
              record ? `/api/captures/${record.capture.id}/video` : undefined
            }
            onPlay={animate}
            onPause={() => cancelAnimationFrame(animation.current)}
            aria-label="Generated beam reference and changed-frequency video"
          />
          <svg viewBox="0 0 400 260" aria-hidden="true">
            <path
              d={`M34 132 Q200 ${132 + deflection} 366 132`}
              fill="none"
              stroke="#edb38b"
              strokeWidth="2"
            />
          </svg>
        </div>
        <div className="home-comparison">
          <div className="toolbar">
            <button
              className="quiet"
              aria-pressed={!changed}
              onClick={() => {
                cancelAnimationFrame(animation.current);
                setChanged(false);
                setDeflection(0);
              }}
            >
              Reference capture
            </button>
            <button
              className="quiet"
              aria-pressed={changed}
              onClick={() => {
                cancelAnimationFrame(animation.current);
                setChanged(true);
                setDeflection(0);
              }}
            >
              Changed frequency
            </button>
          </div>
          <div className="home-reading">
            <span>Measured dominant frequency</span>
            <strong>
              {estimate?.spectrum
                ? estimate.spectrum.peak_hz.toFixed(3) + " Hz"
                : "Awaiting generated demonstration"}
            </strong>
          </div>
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
            window. The tone comes from measured displacement, played faster and
            looped for listening. Amplitude remains experimental.
          </p>
        </div>
      </div>
      <div className="home-principles">
        <section>
          <h2>Evidence before a verdict</h2>
          <p>
            Inspect the recording, displacement and spectrum together. Weak
            texture, uncertain timing or an absent baseline produce insufficient
            evidence.
          </p>
        </section>
        <section>
          <h2>A plan that responds</h2>
          <p>
            The agent changes regions, windows and extraction methods when
            visual evidence is weak. Every action remains in the trace.
          </p>
        </section>
        <section>
          <h2>Review stays human</h2>
          <p>
            A confirmed change requests inspection review. Approval requires a
            reviewer and a reason. Resonance does not certify structural safety.
          </p>
        </section>
      </div>
    </section>
  );
}
