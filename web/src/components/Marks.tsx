import { useId } from "react";
import type { Status } from "../types";

export function Wordmark() {
  const id = "wm-" + useId().replace(/:/g, "");
  return (
    <a className="wordmark" href="#/home">
      <svg viewBox="0 0 150 22" aria-hidden="true">
        <defs>
          <linearGradient id={id} x1="0" x2="1">
            <stop offset="0" stopColor="#3DE0D0" />
            <stop offset="0.5" stopColor="#B98CFF" />
            <stop offset="1" stopColor="#FFB86B" />
          </linearGradient>
        </defs>
        <path
          d="M2 14 C20 14 24 4 44 6 S70 18 90 12 S122 2 148 10"
          fill="none"
          stroke={`url(#${id})`}
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
      <span>Resonance</span>
    </a>
  );
}

export function Arrow({ back = false }: { back?: boolean }) {
  return (
    <svg className="arrow" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d={back ? "M14 8H3M7 3.5L2.5 8 7 12.5" : "M2 8h11M9 3.5L13.5 8 9 12.5"}
      />
    </svg>
  );
}

export function PlayGlyph() {
  return (
    <svg className="play-glyph" viewBox="0 0 14 16" aria-hidden="true">
      <path d="M2 1.5l11 6.5-11 6.5z" />
    </svg>
  );
}

export const statusName = (status: string) =>
  ({
    NORMAL: "No change detected",
    WATCH: "Watch",
    ALERT: "Review requested",
    INSUFFICIENT_EVIDENCE: "Insufficient evidence",
    awaiting_upload: "Awaiting upload",
    queued: "Queued for measurement",
    processing: "Measuring",
    complete: "Complete",
    failed: "Failed",
    expired: "Upload expired",
    pending: "Pending review",
    approved: "Approved",
    rejected: "Rejected",
  })[status] || status.replaceAll("_", " ");

// Shape plus colour, so status never relies on hue alone.
const statusMark: Record<string, string> = {
  NORMAL: "●",
  WATCH: "▲",
  ALERT: "◆",
  INSUFFICIENT_EVIDENCE: "○",
  pending: "▲",
  approved: "●",
  rejected: "✕",
};

export function Badge({ status }: { status: Status | string }) {
  return (
    <span className={`badge ${status.toLowerCase()}`}>
      <span aria-hidden="true">{statusMark[status] ?? "●"}</span>
      {statusName(status)}
    </span>
  );
}

// Draws a measured series as a sparkline; values are downsampled, never invented.
export function Spark({
  values,
  width = 330,
  height = 100,
  className,
}: {
  values: number[];
  width?: number;
  height?: number;
  className?: string;
}) {
  if (values.length < 2) return null;
  const step = Math.max(1, Math.floor(values.length / 240));
  const sampled = values.filter((_, i) => i % step === 0);
  const peak = Math.max(...sampled.map(Math.abs)) || 1;
  const mid = height / 2;
  const d =
    "M" +
    sampled
      .map(
        (v, i) =>
          `${((i / (sampled.length - 1)) * width).toFixed(1)} ${(mid - (v / peak) * (mid - 4)).toFixed(1)}`,
      )
      .join(" L");
  return (
    <svg
      className={"spark " + (className ?? "")}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
