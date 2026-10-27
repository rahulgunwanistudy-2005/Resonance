import { useEffect, useRef, useState } from "react";
import { Dots, Line, Solid } from "../iso/draw";
import { pathOf } from "../iso/kit";
import "../iso/iso.css";
import "./bridge.css";
import {
  BRACING,
  APPROACH_NEAR,
  CAMERA,
  CAMERA_HALO,
  DECK,
  FAR_TRUSS,
  FLOOR,
  GROUND,
  HALO,
  HEIGHT,
  LENS,
  NEAR_RAIL,
  NEAR_TRUSS,
  ROI,
  roiScreen,
  STILL_VIEW,
  TRUCK,
  TRUCK_HALO,
  WIDTH,
  type Item,
  type Panelled,
} from "./geometry";
import {
  deflection,
  launch,
  parked,
  readout,
  restState,
  SPAN,
  step,
  TRUCK_LENGTH,
  truckOpacity,
  type BridgeState,
} from "./model";
import { panelTransforms, truckTransform } from "./pose";

function Draw({ item }: { item: Item }) {
  if (item.kind === "line")
    return (
      <Line d={item.d} tone={item.tone} dashed={item.dashed} flow={item.flow} />
    );
  if (item.kind === "dots")
    return <Dots points={item.points} tone={item.tone} size={item.size} />;
  return (
    <Solid
      paths={item.paths}
      tone={item.tone}
      crease={item.crease}
      lit={item.lit}
      flat={item.flat}
      className={item.className}
      inner={item.inner?.map((seam, i) => (
        <Line key={i} d={seam.d} tone={seam.tone} />
      ))}
    />
  );
}

const items = (list: Item[]) =>
  list.map((item, i) => <Draw key={i} item={item} />);

// Painter's order, back to front. Panelled layers bend with the mode shape.
const LAYERS: [string, Panelled][] = [
  ["far", FAR_TRUSS],
  ["floor", FLOOR],
  ["deck", DECK],
];
const FRONT_LAYERS: [string, Panelled][] = [
  ["rail", NEAR_RAIL],
  ["bracing", BRACING],
  ["near", NEAR_TRUSS],
];

type Refs = Map<string, SVGGElement>;

function Layer({
  name,
  layer,
  pose,
  refs,
}: {
  name: string;
  layer: Panelled;
  pose: BridgeState;
  refs: React.RefObject<Refs>;
}) {
  const transforms = panelTransforms(pose, layer.plane);
  return (
    <g data-layer={name}>
      {layer.panels.map((list, i) => (
        <g
          key={i}
          transform={transforms[i]}
          ref={(node) => {
            if (node) refs.current.set(`${name}-${i}`, node);
            else refs.current.delete(`${name}-${i}`);
          }}
        >
          {items(list)}
        </g>
      ))}
    </g>
  );
}

const sight = (state: BridgeState) => {
  const end = roiScreen(deflection(state, ROI[0]![0] - 12));
  return pathOf([LENS, end]);
};

type Props = {
  /** "hero" is framed and live; "still" is a quiet picture. */
  variant?: "hero" | "still";
  /** Still figures only: park a truck on the span. */
  truck?: boolean;
  label?: string;
  caption?: React.ReactNode;
};

export function BridgeFigure({
  variant = "still",
  truck = false,
  label,
  caption,
}: Props) {
  const live = variant === "hero";
  const [pose] = useState<BridgeState>(() =>
    live ? restState() : parked(truck ? SPAN * 0.55 + TRUCK_LENGTH / 2 : null),
  );
  const state = useRef<BridgeState>(pose);
  const refs = useRef<Refs>(new Map());
  const truckRef = useRef<SVGGElement>(null);
  const sightRef = useRef<SVGPathElement>(null);
  const readoutRef = useRef<HTMLSpanElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const kick = useRef<() => void>(() => {});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!live || !root.current) return;
    const node = root.current;
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    let last = 0;
    let inView = false;

    const paint = (s: BridgeState) => {
      for (const [name, layer] of [...LAYERS, ...FRONT_LAYERS]) {
        const transforms = panelTransforms(s, layer.plane);
        transforms.forEach((t, i) =>
          refs.current.get(`${name}-${i}`)?.setAttribute("transform", t),
        );
      }
      const t = truckRef.current;
      if (t) {
        if (s.front === null) t.setAttribute("opacity", "0");
        else {
          t.setAttribute("transform", truckTransform(s, s.front));
          t.setAttribute("opacity", truckOpacity(s.front).toFixed(2));
        }
      }
      sightRef.current?.setAttribute("d", sight(s));
      const text = readout(s);
      if (readoutRef.current && readoutRef.current.textContent !== text)
        readoutRef.current.textContent = text;
      setBusy(s.front !== null);
    };

    const tick = (now: number) => {
      const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
      last = now;
      step(state.current, dt, true);
      paint(state.current);
      frame = inView ? requestAnimationFrame(tick) : 0;
    };
    const start = () => {
      if (calm.matches) {
        state.current = parked(SPAN * 0.55 + TRUCK_LENGTH / 2);
        paint(state.current);
        return;
      }
      if (!frame && inView) {
        last = 0;
        frame = requestAnimationFrame(tick);
      }
    };
    kick.current = () => {
      if (calm.matches) return;
      launch(state.current);
      start();
    };
    const observer = new IntersectionObserver((entries) => {
      inView = Boolean(entries.at(-1)?.isIntersecting);
      if (inView) start();
      else {
        cancelAnimationFrame(frame);
        frame = 0;
      }
    });
    observer.observe(node);
    calm.addEventListener("change", start);
    return () => {
      observer.disconnect();
      calm.removeEventListener("change", start);
      cancelAnimationFrame(frame);
    };
  }, [live]);

  const front = pose.front;
  const svg = (
    <svg
      className="iso-svg bridge-svg"
      viewBox={live ? `0 0 ${WIDTH} ${HEIGHT}` : STILL_VIEW}
      preserveAspectRatio={live ? undefined : "xMidYMid slice"}
      {...(label
        ? { role: "img", "aria-label": label }
        : { "aria-hidden": true })}
      focusable="false"
    >
      <path className="iso-halo" d={HALO} />
      {items(GROUND)}
      {LAYERS.map(([name, layer]) => (
        <Layer key={name} name={name} layer={layer} pose={pose} refs={refs} />
      ))}
      <g
        ref={truckRef}
        className="bridge-truck"
        opacity={front === null ? 0 : 1}
        transform={front === null ? undefined : truckTransform(pose, front)}
      >
        <path className="iso-halo" d={TRUCK_HALO} />
        {items(TRUCK)}
      </g>
      {items(APPROACH_NEAR)}
      {FRONT_LAYERS.map(([name, layer]) => (
        <Layer key={name} name={name} layer={layer} pose={pose} refs={refs} />
      ))}
      <path className="iso-halo bridge-rig-halo" d={CAMERA_HALO} />
      {items(CAMERA)}
      <path ref={sightRef} className="bridge-sight" d={sight(pose)} />
    </svg>
  );

  if (!live)
    return (
      <div className="iso bridge-iso bridge-still" ref={root}>
        {svg}
      </div>
    );

  return (
    <figure className="iso bridge-iso bridge-hero" ref={root}>
      <div className="iso-plate">
        <div className="iso-plate-corners">
          <span className="iso-plate-corner" data-corner="fig">
            Fig. 1
          </span>
          <span className="iso-plate-corner" data-corner="title">
            Through-truss span, first bending mode
          </span>
          <span className="iso-plate-corner" data-corner="hint">
            <button
              type="button"
              className="bridge-send"
              onClick={() => kick.current()}
              aria-disabled={busy}
            >
              Send a truck
            </button>
          </span>
          <span
            className="iso-plate-corner"
            data-corner="readout"
            ref={readoutRef}
          >
            {readout(pose)}
          </span>
        </div>
        {svg}
      </div>
      {caption && <figcaption className="iso-legend">{caption}</figcaption>}
    </figure>
  );
}
