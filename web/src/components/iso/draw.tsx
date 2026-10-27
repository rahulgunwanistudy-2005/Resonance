// React drawing components from the Anatomy skill's kit (MIT License, Copyright (c) 2026 Ryan).
import type { Flat, LineTone, SolidPaths, Tone } from "./kit";

type SolidProps = {
  paths: SolidPaths;
  tone?: Tone;
  crease?: Tone | "none";
  lit?: boolean;
  flat?: boolean;
  className?: string;
  inner?: React.ReactNode;
};

export function Solid({
  paths,
  tone = "hi",
  crease = "faint",
  lit = false,
  flat = false,
  className,
  inner,
}: SolidProps) {
  return (
    <g
      className={className ? `iso-solid ${className}` : "iso-solid"}
      data-lit={lit ? "" : undefined}
    >
      <path className="iso-fill" d={paths.fill} />
      {!flat &&
        paths.shades.map((d, shade) =>
          d ? (
            <path key={shade} className="iso-shade" data-shade={shade} d={d} />
          ) : null,
        )}
      {!flat && paths.top && <path className="iso-top" d={paths.top} />}
      {crease !== "none" && paths.crease && (
        <path
          className="iso-line iso-crease"
          data-tone={crease}
          d={paths.crease}
        />
      )}
      {crease !== "none" && paths.bevel && (
        <path
          className="iso-line iso-bevel"
          data-tone={crease}
          d={paths.bevel}
        />
      )}
      {inner}
      <path className="iso-line iso-edge" data-tone={tone} d={paths.outline} />
    </g>
  );
}

export function Line({
  d,
  tone = "lo",
  dashed = false,
  flow = false,
  className,
}: {
  d: string;
  tone?: LineTone;
  dashed?: boolean;
  flow?: boolean;
  className?: string;
}) {
  if (!d) return null;
  return (
    <path
      className={className ? `iso-line ${className}` : "iso-line"}
      data-tone={tone}
      data-dashed={dashed ? "" : undefined}
      data-flow={flow ? "" : undefined}
      d={d}
    />
  );
}

const tenth = (value: number) => Math.round(value * 10) / 10;

export function Dots({
  points,
  size = 0.5,
  tone = "mid",
}: {
  points: Flat[];
  size?: number;
  tone?: Tone;
}) {
  return (
    <g className="iso-dots" data-tone={tone}>
      {points.map(([x, y], index) => (
        <circle key={index} cx={tenth(x)} cy={tenth(y)} r={size} />
      ))}
    </g>
  );
}
