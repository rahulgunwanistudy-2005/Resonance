import { useEffect, useRef, useState, type PointerEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, json } from "../api";
import type { Roi, Bridge } from "../types";
export function Upload({
  onComplete,
}: {
  onComplete: (bridge: string, capture: string) => void;
}) {
  const [existing, setExisting] = useState("");
  const bridges = useQuery({
    queryKey: ["bridges"],
    queryFn: () => api<Bridge[]>("/bridges"),
  });
  const [file, setFile] = useState<File | null>(null),
    [url, setUrl] = useState(""),
    [dimensions, setDimensions] = useState({ width: 384, height: 256 });
  const [roi, setRoi] = useState<Roi>({
    id: "deck",
    x: 128,
    y: 96,
    width: 96,
    height: 64,
  });
  const [points, setPoints] = useState<[number, number][]>([]),
    [length, setLength] = useState(""),
    [fps, setFps] = useState("60"),
    [high, setHigh] = useState("15"),
    [low, setLow] = useState("1"),
    [temperature, setTemperature] = useState("");
  const [confirmed, setConfirmed] = useState(false),
    [name, setName] = useState("New camera measurement"),
    [mode, setMode] = useState<"roi" | "scale">("roi"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [progress, setProgress] = useState("");
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );
  const start = useRef<[number, number] | null>(null);
  function point(e: PointerEvent<SVGSVGElement>): [number, number] {
    const box = e.currentTarget.getBoundingClientRect();
    return [
      Math.round(((e.clientX - box.left) / box.width) * dimensions.width),
      Math.round(((e.clientY - box.top) / box.height) * dimensions.height),
    ];
  }
  function choose(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.files?.[0];
    if (!value) return;
    if (url) URL.revokeObjectURL(url);
    if (value.size > 200_000_000) {
      setFile(null);
      setUrl("");
      setError("Video exceeds the upload size limit. Shorten or compress it.");
      return;
    }
    setFile(value);
    setUrl(URL.createObjectURL(value));
    setPoints([]);
    setError("");
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !confirmed) {
      setError("Choose a video and confirm the camera acquisition frame rate.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const calibration =
        points.length === 2 && Number(length) > 0
          ? {
              mm_per_pixel:
                Number(length) /
                Math.hypot(
                  points[1][0] - points[0][0],
                  points[1][1] - points[0][1],
                ),
              reference_length_mm: Number(length),
              points,
            }
          : null;
      if (calibration && !Number.isFinite(calibration.mm_per_pixel))
        throw new Error("Choose two different calibration points.");
      setProgress("Creating measurement");
      const bridge = existing
        ? bridges.data?.find((item) => item.bridge.id === existing)
        : await api<Bridge>("/bridges", {
            method: "POST",
            body: json({
              name,
              band: { low_hz: Number(low), high_hz: Number(high) },
              rois: [roi],
              calibration,
            }),
          });
      if (!bridge)
        throw new Error("Choose an available bridge or enroll a new one.");
      const ticket = await api<{
        capture_id: string;
        upload_url: string;
        upload_token: string;
      }>("/captures", {
        method: "POST",
        body: json({
          bridge_id: bridge.bridge.id,
          rois: [roi],
          calibration,
          acquisition_fps: Number(fps),
          acquisition_fps_verified: confirmed,
          temperature_c: temperature === "" ? null : Number(temperature),
        }),
      });
      setProgress("Uploading video");
      const response = await fetch(ticket.upload_url, {
        method: "PUT",
        headers: {
          Authorization: "Bearer " + ticket.upload_token,
          "Content-Type": "application/octet-stream",
        },
        body: file,
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(
          data.error || "Video upload failed. Start a new upload.",
        );
      }
      onComplete(bridge.bridge.id, ticket.capture_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Measurement could not start.");
    } finally {
      setBusy(false);
      setProgress("");
    }
  }
  return (
    <form className="upload-layout" onSubmit={submit}>
      <div>
        <h1>Measure a video</h1>
        <p className="intro">
          Choose a textured part of the deck. Give the measurement a scale, then
          let the evidence set the next step.
        </p>
        <label className="file-picker">
          Choose a video
          <input type="file" accept="video/*" onChange={choose} />
        </label>
        <p className="privacy">
          Uploads are removed after a day by the local worker. Only measurements
          and derived evidence remain. Private uploads are not publicly
          replayed.
        </p>
        {url ? (
          <>
            <div className="selection-video">
              <video
                src={url}
                controls
                onLoadedMetadata={(e) => {
                  const v = e.currentTarget;
                  setDimensions({ width: v.videoWidth, height: v.videoHeight });
                  setRoi({
                    id: "deck",
                    x: Math.round(v.videoWidth * 0.4),
                    y: Math.round(v.videoHeight * 0.4),
                    width: Math.min(128, Math.round(v.videoWidth * 0.2)),
                    height: Math.min(96, Math.round(v.videoHeight * 0.2)),
                  });
                }}
              />
              <svg
                viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
                aria-label="Region and scale selection"
                onPointerDown={(e) => {
                  start.current = point(e);
                  e.currentTarget.setPointerCapture(e.pointerId);
                }}
                onPointerUp={(e) => {
                  const p = point(e);
                  if (mode === "scale") {
                    setPoints((old) => (old.length >= 2 ? [p] : [...old, p]));
                  } else if (start.current) {
                    const [x, y] = start.current;
                    setRoi({
                      id: "deck",
                      x: Math.max(0, Math.min(x, p[0])),
                      y: Math.max(0, Math.min(y, p[1])),
                      width: Math.max(16, Math.abs(x - p[0])),
                      height: Math.max(16, Math.abs(y - p[1])),
                    });
                  }
                  start.current = null;
                }}
              >
                <rect
                  x={roi.x}
                  y={roi.y}
                  width={roi.width}
                  height={roi.height}
                  className="roi"
                />
                {points.map((p, i) => (
                  <circle
                    key={i}
                    cx={p[0]}
                    cy={p[1]}
                    r={Math.max(3, dimensions.width / 100)}
                    fill="#f4f7f2"
                  />
                ))}
                {points.length === 2 && (
                  <line
                    x1={points[0][0]}
                    y1={points[0][1]}
                    x2={points[1][0]}
                    y2={points[1][1]}
                    stroke="white"
                    strokeWidth={2}
                  />
                )}
              </svg>
            </div>
            <div className="toolbar">
              <button
                type="button"
                className="quiet"
                aria-pressed={mode === "roi"}
                onClick={() => setMode("roi")}
              >
                Draw measurement region
              </button>
              <button
                type="button"
                className="quiet"
                aria-pressed={mode === "scale"}
                onClick={() => setMode("scale")}
              >
                Select scale points
              </button>
            </div>
            <p className="help">
              Drag to set a region, or use the coordinate fields. Scale mode
              uses two clicks. Video controls remain below the selection
              overlay.
            </p>
          </>
        ) : (
          <div className="upload-empty">
            <svg viewBox="0 0 400 160" aria-hidden="true">
              <path
                d="M15 118H385M65 118V143M335 118V143M65 118Q200 35 335 118M100 118V90M150 118V66M200 118V59M250 118V66M300 118V90"
                fill="none"
                stroke="currentColor"
                strokeWidth="4"
              />
            </svg>
            <p>Your recording becomes the instrument.</p>
          </div>
        )}
      </div>
      <aside className="form-panel">
        <h2>Capture settings</h2>
        <label>
          Record for
          <select
            aria-label="Record for"
            value={existing}
            onChange={(e) => {
              setExisting(e.target.value);
              const selected = bridges.data?.find(
                (item) => item.bridge.id === e.target.value,
              );
              if (selected) {
                setLow(String(selected.bridge.band.low_hz));
                setHigh(String(selected.bridge.band.high_hz));
              }
            }}
          >
            <option value="">New bridge or experiment</option>
            {bridges.data
              ?.filter((item) => !item.synthetic)
              .map((item) => (
                <option key={item.bridge.id} value={item.bridge.id}>
                  {item.bridge.name}
                </option>
              ))}
          </select>
        </label>
        {existing && (
          <p className="help">
            This capture joins the selected bridge's history. Keep the view,
            prior and calibration consistent with the reference recordings.
          </p>
        )}
        <label>
          Bridge or experiment name
          <input
            disabled={!!existing}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={160}
          />
        </label>
        <div className="field-pair">
          <label>
            Lower band (Hz)
            <input
              type="number"
              min="0.1"
              step="0.1"
              disabled={!!existing}
              value={low}
              onChange={(e) => setLow(e.target.value)}
              required
            />
          </label>
          <label>
            Upper band (Hz)
            <input
              type="number"
              min="0.2"
              step="0.1"
              disabled={!!existing}
              value={high}
              onChange={(e) => setHigh(e.target.value)}
              required
            />
          </label>
        </div>
        <label>
          Acquisition frame rate
          <input
            type="number"
            min="1"
            max="1000"
            value={fps}
            onChange={(e) => setFps(e.target.value)}
            required
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          I confirmed the camera acquisition rate, including slow-motion
          settings.
        </label>
        <label>
          Recording temperature (°C, optional)
          <input
            type="number"
            min="-100"
            max="100"
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
          />
        </label>
        <fieldset>
          <legend>Region coordinates</legend>
          <div className="field-pair">
            {(["x", "y", "width", "height"] as const).map((key) => (
              <label key={key}>
                {key}
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
        <label>
          Known scale length (mm, optional)
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={length}
            onChange={(e) => setLength(e.target.value)}
          />
        </label>
        <p className="help">
          The scale must lie in the motion plane. Amplitude remains experimental
          even after geometric calibration.
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy || !file} type="submit">
          {busy ? progress : "Run measurement"}
        </button>
        <p className="help">
          Triage support. This measurement does not replace inspection.
        </p>
      </aside>
    </form>
  );
}
