// Every static path of the bridge figure, computed once at module load.
// World units: x along the span, y across it (+y toward the viewer), z up.
// The deck surface is z = 0.
import {
  cylinder,
  fitProjection,
  haloOf,
  iso,
  lineOnTop,
  pathOf,
  segment,
  sideSeam,
  slabOf,
  type Flat,
  type LineTone,
  type Plan,
  type Point3,
  type Projection,
  type SolidPaths,
  type Tone,
} from "../iso/kit";
import { beam, drum, plateXZ, sub, unit } from "../iso/prism";
import { PANEL, PANELS, SPAN, TRUCK_LENGTH } from "./model";

export type Item =
  | {
      kind: "solid";
      paths: SolidPaths;
      tone?: Tone;
      crease?: Tone | "none";
      lit?: boolean;
      flat?: boolean;
      className?: string;
      inner?: { d: string; tone: LineTone }[];
    }
  | {
      kind: "line";
      d: string;
      tone?: LineTone;
      dashed?: boolean;
      flow?: boolean;
    }
  | { kind: "dots"; points: Flat[]; size?: number; tone?: Tone };

/** Plane a panel group lies in, used to shear it with the mode shape. */
export type Plane = { vertical: number } | { horizontal: number };
export type Panelled = { plane: Plane; panels: Item[][] };

export const WIDTH = 900;
export const HEIGHT = 470;
const AZIMUTH = 60;
const ELEVATION = 36; // high enough to see the deck between the trusses

// Truss
export const TRUSS_Y = 34;
const HEIGHT_T = 56;
export const Z_BOTTOM = -9; // bottom chord centre line
const Z_TOP = Z_BOTTOM + HEIGHT_T;
const CHORD: [number, number] = [6, 8];
const POST: [number, number] = [5, 4.6];
const TIE: [number, number] = [4, 3.4];
const DECK_HALF = 28;
const LANE_Y = 13;
// Site
const BANK_Y: [number, number] = [-66, 104];
const BANK_X = 112; // how far each bank runs back from the river
const BANK_TOP = -5;
const BANK_BOTTOM = -60;
const SEAT = -24;
const WATER = -50;
// Camera on the near bank
const RIG: Point3 = [-70, 76, BANK_TOP];
export const ROI: Point3[] = [
  [SPAN / 2, TRUSS_Y + CHORD[0] / 2 + 0.8, Z_BOTTOM],
  [SPAN / 4, TRUSS_Y + CHORD[0] / 2 + 0.8, Z_BOTTOM],
];

const extremes: Point3[] = [
  [-BANK_X, BANK_Y[0], BANK_BOTTOM],
  [-BANK_X, BANK_Y[1], BANK_BOTTOM],
  [-BANK_X, BANK_Y[0], 8],
  [SPAN + BANK_X, BANK_Y[0], BANK_BOTTOM],
  [SPAN + BANK_X, BANK_Y[1], BANK_BOTTOM],
  [SPAN + BANK_X, BANK_Y[0], 8],
  [PANEL, -TRUSS_Y, Z_TOP + 6],
  [SPAN - PANEL, -TRUSS_Y, Z_TOP + 6],
  [RIG[0], RIG[1] + 20, BANK_BOTTOM],
];
export const P: Projection = fitProjection(extremes, WIDTH, HEIGHT, {
  pad: 18,
  azimuth: AZIMUTH,
  elevation: ELEVATION,
});

/** A tighter view of the span for small still pictures, as an SVG viewBox. */
export const STILL_VIEW = (() => {
  const pts = [
    [-40, -TRUSS_Y, Z_TOP + 6],
    [-40, TRUSS_Y + 30, WATER],
    [SPAN + 40, -TRUSS_Y, Z_TOP + 6],
    [SPAN + 40, TRUSS_Y + 30, WATER],
  ].map((p) => iso(p as Point3, P));
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs);
  const y0 = Math.min(...ys);
  return [x0, y0, Math.max(...xs) - x0, Math.max(...ys) - y0]
    .map((v) => v.toFixed(1))
    .join(" ");
})();

const X = (i: number) => i * PANEL;
const solid = (
  paths: SolidPaths,
  tone: Tone = "mid",
  extra: Partial<Extract<Item, { kind: "solid" }>> = {},
): Item => ({ kind: "solid", paths, tone, ...extra });
const line = (
  d: string,
  tone: LineTone = "lo",
  extra: { dashed?: boolean; flow?: boolean } = {},
): Item => ({ kind: "line", d, tone, ...extra });
const dots = (points: Point3[], tone: Tone = "mid", size = 0.55): Item => ({
  kind: "dots",
  points: points.map((p) => iso(p, P)),
  tone,
  size,
});
const slab = (plan: Plan, z0: number, z1: number, steps = 2, bevel = 0) =>
  slabOf(plan, z0, z1 - z0, P, steps, bevel);
const box = (
  x0: number,
  x1: number,
  y0: number,
  y1: number,
  z0: number,
  z1: number,
  r = 0.6,
  bevel = 0,
) => slab({ x: x0, y: y0, w: x1 - x0, d: y1 - y0, r }, z0, z1, 2, bevel);

/* ----------------------------------------------------------------- site */

function bankItems(side: "left" | "right"): Item[] {
  const left = side === "left";
  const items: Item[] = [];
  const bank: Plan = left
    ? {
        x: -BANK_X,
        y: BANK_Y[0],
        w: BANK_X - 26,
        d: BANK_Y[1] - BANK_Y[0],
        r: 4,
      }
    : {
        x: SPAN + 26,
        y: BANK_Y[0],
        w: BANK_X - 26,
        d: BANK_Y[1] - BANK_Y[0],
        r: 4,
      };
  const strata = [-20, -40].map((z) => ({
    d: sideSeam(bank, z, P, 2),
    tone: "faint" as LineTone,
  }));
  items.push(
    solid(slab(bank, BANK_BOTTOM, BANK_TOP, 2), "lo", { inner: strata }),
  );
  // abutment: footing block with bridge seat, backwall on top
  const [a0, a1] = left ? [-26, 12] : [SPAN - 12, SPAN + 26];
  const [w0, w1] = left ? [-26, -1] : [SPAN + 1, SPAN + 26];
  const lifts = [-42].map((z) => ({
    d: sideSeam({ x: a0, y: -52, w: a1 - a0, d: 104, r: 0.6 }, z, P, 2),
    tone: "faint" as LineTone,
  }));
  items.push(
    solid(box(a0, a1, -52, 52, BANK_BOTTOM + 2, SEAT, 0.6, 0.8), "mid", {
      inner: lifts,
    }),
  );
  items.push(solid(box(w0, w1, -52, 52, SEAT, BANK_TOP, 0.6, 0.6), "mid"));
  // approach slab with lane lines and the far guardrail
  const [r0, r1] = left ? [-BANK_X, -1] : [SPAN + 1, SPAN + BANK_X];
  items.push(solid(box(r0, r1, -DECK_HALF, DECK_HALF, BANK_TOP, 0), "lo"));
  items.push(line(lineOnTop([r0, 0], [r1, 0], 0, P), "lo", { dashed: true }));
  for (const y of [-DECK_HALF + 4, DECK_HALF - 4])
    items.push(line(lineOnTop([r0, y], [r1, y], 0, P), "faint"));
  items.push(...guardrail(r0 + 10, r1 - 6, -DECK_HALF - 3));
  // bearings on the seat under each truss
  const bx = left ? 4 : SPAN - 4;
  for (const y of [-TRUSS_Y, TRUSS_Y]) items.push(...bearing(bx, y));
  return items;
}

function guardrail(x0: number, x1: number, y: number): Item[] {
  const items: Item[] = [];
  const count = Math.max(2, Math.round((x1 - x0) / 20));
  for (let i = 0; i <= count; i++) {
    const x = x0 + ((x1 - x0) * i) / count;
    items.push(
      solid(box(x - 1.4, x + 1.4, y - 1.4, y + 1.4, 0, 8.5, 0.4), "lo"),
    );
  }
  items.push(
    solid(box(x0 - 2, x1 + 2, y + 1.4, y + 2.6, 4.2, 8.2, 0.3), "mid"),
  );
  return items;
}

function bearing(x: number, y: number): Item[] {
  const zs = Z_BOTTOM - CHORD[1] / 2; // underside of the bottom chord
  return [
    solid(box(x - 7, x + 7, y - 8, y + 8, SEAT, SEAT + 3.5, 0.8, 0.5), "lo"),
    solid(
      box(x - 6, x + 6, y - 6.5, y + 6.5, SEAT + 3.5, SEAT + 5, 0.4),
      "mid",
    ),
    dots(
      [
        [x - 4.6, y - 5, SEAT + 5],
        [x + 4.6, y - 5, SEAT + 5],
        [x - 4.6, y + 5, SEAT + 5],
        [x + 4.6, y + 5, SEAT + 5],
      ],
      "hi",
      0.6,
    ),
    solid(
      box(x - 3.6, x + 3.6, y - 4.6, y + 4.6, SEAT + 5, zs - 1.6, 1.2),
      "mid",
    ),
    solid(box(x - 5, x + 5, y - 4.2, y + 4.2, zs - 1.6, zs, 0.3), "mid"),
  ];
}

function water(): Item[] {
  const plan: Plan = {
    x: -26,
    y: BANK_Y[0],
    w: SPAN + 52,
    d: BANK_Y[1] - BANK_Y[0],
    r: 0,
  };
  const items: Item[] = [
    solid(slab(plan, BANK_BOTTOM + 2, WATER, 2), "lo", {
      className: "bridge-water",
    }),
  ];
  for (let x = 30; x < SPAN - 10; x += 34) {
    const wobble = (x * 37) % 11;
    items.push(
      line(
        lineOnTop([x + wobble, BANK_Y[0]], [x + wobble, BANK_Y[1]], WATER, P),
        "lo",
        {
          flow: true,
        },
      ),
    );
  }
  return items;
}

export const GROUND: Item[] = [
  ...water(),
  ...bankItems("left"),
  ...bankItems("right"),
];
export const HALO = haloOf(
  {
    x: -BANK_X,
    y: BANK_Y[0],
    w: SPAN + 2 * BANK_X,
    d: BANK_Y[1] - BANK_Y[0],
    r: 8,
  },
  BANK_BOTTOM,
  0,
  P,
);

/* ---------------------------------------------------------------- truss */

const empty = (): Item[][] => Array.from({ length: PANELS }, () => []);

function gussetOutline(x: number, z: number, top: boolean, end: -1 | 0 | 1) {
  const dir = top ? -1 : 1; // toward the web
  const reach = 13 * dir;
  const lo = z - 5 * dir;
  const left = end === 1 ? x - 3 : x - 9;
  const right = end === -1 ? x + 3 : x + 9;
  const pts: [number, number][] = [
    [left, lo],
    [right, lo],
    [right, z + 5 * dir],
    [Math.min(right, x + 4), z + reach],
    [Math.max(left, x - 4), z + reach],
    [left, z + 5 * dir],
  ];
  // keep the polygon counter-clockwise in (x, z)
  return top ? pts.reverse() : pts;
}

function truss(y: number, near: boolean): Panelled {
  const panels = empty();
  const face = near ? y + CHORD[0] / 2 : y + CHORD[0] / 2 - 0.1; // gussets on the side facing the viewer
  const gy = near ? face : y - CHORD[0] / 2 + 3 + 0.2;
  const across: Point3 = [0, 1, 0];
  const at = (x: number, z: number): Point3 => [x, y, z];
  const tone: Tone = "hi";
  for (let i = 0; i < PANELS; i++) {
    const list = panels[i]!;
    const x0 = X(i);
    const x1 = X(i + 1);
    // bottom chord, the element the camera watches on the near truss
    list.push(
      solid(
        beam(at(x0, Z_BOTTOM), at(x1, Z_BOTTOM), across, CHORD[0], CHORD[1], P),
        tone,
        {
          lit: near,
        },
      ),
    );
    // top chord or inclined end post
    if (i === 0)
      list.push(
        solid(
          beam(at(x0, Z_BOTTOM), at(x1, Z_TOP), across, CHORD[0], CHORD[1], P),
          tone,
        ),
      );
    else if (i === PANELS - 1)
      list.push(
        solid(
          beam(at(x0, Z_TOP), at(x1, Z_BOTTOM), across, CHORD[0], CHORD[1], P),
          tone,
        ),
      );
    else
      list.push(
        solid(
          beam(at(x0, Z_TOP), at(x1, Z_TOP), across, CHORD[0], CHORD[1], P),
          tone,
        ),
      );
    // vertical at the left node
    if (i > 0)
      list.push(
        solid(
          beam(at(x0, Z_BOTTOM), at(x0, Z_TOP), across, POST[0], POST[1], P),
          tone,
        ),
      );
    // Pratt diagonals slope down toward midspan
    if (i > 0 && i < PANELS - 1) {
      const d =
        i < PANELS / 2
          ? beam(at(x0, Z_TOP), at(x1, Z_BOTTOM), across, TIE[0], TIE[1], P)
          : beam(at(x0, Z_BOTTOM), at(x1, Z_TOP), across, TIE[0], TIE[1], P);
      list.push(solid(d, tone));
    }
    // gusset plates and their rivets at the left node (and the last node)
    const nodes: [number, number, boolean, -1 | 0 | 1][] = [
      [x0, Z_BOTTOM, false, i === 0 ? 1 : 0],
    ];
    if (i > 0) nodes.push([x0, Z_TOP, true, 0]);
    if (i === PANELS - 1) nodes.push([x1, Z_BOTTOM, false, -1]);
    for (const [gx, gz, top, end] of nodes) {
      const outline = gussetOutline(gx, gz, top, end);
      list.push(solid(plateXZ(outline, gy, 0.9, P), "mid", { crease: "none" }));
      const ry = gy + 0.9;
      const dir = top ? -1 : 1;
      const rivets: Point3[] = [];
      for (const dx of [-5.5, -2, 2, 5.5]) {
        if ((end === 1 && dx < -2) || (end === -1 && dx > 2)) continue;
        rivets.push(
          [gx + dx, ry, gz - 2.2 * dir],
          [gx + dx, ry, gz + 2.2 * dir],
        );
      }
      rivets.push([gx - 1.6, ry, gz + 9 * dir], [gx + 1.6, ry, gz + 9 * dir]);
      list.push(dots(rivets, near ? "hi" : "lo", near ? 0.55 : 0.45));
    }
  }
  if (near)
    for (const [x, , z] of ROI) {
      // painted speckle targets on the watched chord
      const i = Math.min(PANELS - 1, Math.floor(x / PANEL));
      const tx = x + (x === SPAN / 2 ? -12 : 0);
      panels[i]!.push(
        solid(
          plateXZ(
            [
              [tx - 4, z - 3],
              [tx + 4, z - 3],
              [tx + 4, z + 3],
              [tx - 4, z + 3],
            ],
            face + 0.01,
            0.4,
            P,
          ),
          "hi",
          {
            className: "bridge-target",
            crease: "none",
          },
        ),
      );
    }
  return { plane: { vertical: y }, panels };
}

export const FAR_TRUSS = truss(-TRUSS_Y, false);
export const NEAR_TRUSS = truss(TRUSS_Y, true);

/* ----------------------------------------------------------------- deck */

function floorBeams(): Panelled {
  const panels = empty();
  for (let i = 0; i <= PANELS; i++) {
    const x = X(i);
    const list = panels[Math.min(i, PANELS - 1)]!;
    list.push(
      solid(box(x - 2.4, x + 2.4, -TRUSS_Y, TRUSS_Y, -17, -5, 0.3), "lo"),
    );
  }
  return { plane: { horizontal: -5 }, panels };
}

function deck(): Panelled {
  const panels = empty();
  for (let i = 0; i < PANELS; i++) {
    const x0 = X(i);
    const x1 = X(i + 1);
    const list = panels[i]!;
    list.push(solid(box(x0, x1, -DECK_HALF, DECK_HALF, -5, 0, 0.2), "mid"));
    list.push(line(lineOnTop([x0, 0], [x1, 0], 0, P), "lo", { dashed: true }));
    for (const y of [-DECK_HALF + 4, DECK_HALF - 4])
      list.push(line(lineOnTop([x0, y], [x1, y], 0, P), "faint"));
    // far curb and guardrail; the near ones are drawn after the truck
    list.push(
      solid(box(x0, x1, -DECK_HALF - 2, -DECK_HALF + 1.5, 0, 2.2, 0.2), "mid"),
    );
    list.push(...railPanel(x0, x1, -TRUSS_Y + CHORD[0] / 2 + 1.4, i));
  }
  return { plane: { horizontal: 0 }, panels };
}

function railPanel(x0: number, x1: number, y: number, i: number): Item[] {
  const items: Item[] = [];
  for (const x of [x0 + PANEL / 2])
    items.push(solid(box(x - 1.2, x + 1.2, y - 1, y + 1, 0, 8, 0.3), "lo"));
  const a = i === 0 ? x0 + 6 : x0;
  const b = i === PANELS - 1 ? x1 - 6 : x1;
  items.push(solid(box(a, b, y - 1, y + 0.6, 4, 8, 0.2), "mid"));
  return items;
}

export const FLOOR = floorBeams();
export const DECK = deck();

function nearRail(): Panelled {
  const panels = empty();
  for (let i = 0; i < PANELS; i++) {
    const x0 = X(i);
    const x1 = X(i + 1);
    panels[i]!.push(
      solid(box(x0, x1, DECK_HALF - 1.5, DECK_HALF + 2, 0, 2.2, 0.2), "mid"),
    );
    panels[i]!.push(...railPanel(x0, x1, TRUSS_Y - CHORD[0] / 2 - 1.4, i));
  }
  return { plane: { vertical: TRUSS_Y - 4 }, panels };
}
export const NEAR_RAIL = nearRail();

/* ------------------------------------------------------- top bracing */

function bracing(): Panelled {
  const panels = empty();
  const strut = (x: number, z: number) =>
    beam([x, -TRUSS_Y, z], [x, TRUSS_Y, z], [1, 0, 0], 3.6, 5, P);
  for (let i = 1; i < PANELS; i++)
    panels[i]!.push(solid(strut(X(i), Z_TOP), "mid"));
  // lateral X bracing between the struts
  for (let i = 1; i < PANELS - 1; i++) {
    const x0 = X(i);
    const x1 = X(i + 1);
    const z = Z_TOP + 2.6;
    panels[i]!.push(
      solid(
        beam(
          [x0 + 2, -TRUSS_Y + 3, z],
          [x1 - 2, TRUSS_Y - 3, z],
          [0, 0, 1],
          1.4,
          2,
          P,
        ),
        "lo",
      ),
      solid(
        beam(
          [x0 + 2, TRUSS_Y - 3, z],
          [x1 - 2, -TRUSS_Y + 3, z],
          [0, 0, 1],
          1.4,
          2,
          P,
        ),
        "lo",
      ),
    );
  }
  // portal frames between the inclined end posts
  for (const [i, x] of [
    [0, PANEL * 0.78],
    [PANELS - 1, SPAN - PANEL * 0.78],
  ] as const) {
    const z = Z_BOTTOM + HEIGHT_T * 0.78;
    panels[i]!.push(
      solid(beam([x, -TRUSS_Y, z], [x, TRUSS_Y, z], [1, 0, 0], 3, 9, P), "mid"),
    );
    // knee braces from the underside of the strut down to the end posts
    const postX = (zz: number) => {
      const run = (PANEL * (zz - Z_BOTTOM)) / HEIGHT_T;
      return i === 0 ? run : SPAN - run;
    };
    for (const side of [-1, 1]) {
      const top: Point3 = [postX(z - 4.5), side * (TRUSS_Y - 15), z - 4.5];
      const foot: Point3 = [postX(z - 17), side * (TRUSS_Y - 3), z - 17];
      panels[i]!.push(solid(beam(top, foot, [1, 0, 0], 2.4, 2.4, P), "lo"));
    }
  }
  return { plane: { horizontal: Z_TOP }, panels };
}
export const BRACING = bracing();

/* ---------------------------------------------------------------- truck */

/**
 * Truck in the near lane, driving toward −x (right-hand traffic), built with
 * its front bumper at x = 0 and its body toward +x. Its rear and near side
 * face the viewer.
 */
function truck(): Item[] {
  const y0 = LANE_Y - 7;
  const y1 = LANE_Y + 7;
  const items: Item[] = [];
  const axles = [9, 23, 27, 62, 66];
  const wheel = (x: number, y: number) =>
    solid(drum([x, y, 4.2], [0, 1, 0], 4.2, 2.6, P, 22), "lo");
  // the wheels sit inset under the body, so all of them go first
  for (const x of axles) items.push(wheel(x, y0 + 1.3));
  for (const x of axles) items.push(wheel(x, y1 - 1.3 - 2.6));
  // tractor: chassis, hood, sleeper cab with side window, exhaust stack
  items.push(solid(box(1, 28, y0 + 1.6, y1 - 1.6, 5.5, 8.5, 0.2), "lo"));
  items.push(solid(box(1, 8, y0 + 1.2, y1 - 1.2, 8.5, 15, 1.2, 0.4), "mid"));
  items.push(solid(box(8, 20, y0 + 0.6, y1 - 0.6, 8.5, 25, 1.2, 0.6), "mid"));
  const window: Point3[] = [
    [9.5, y1 - 0.6, 17],
    [14.5, y1 - 0.6, 17],
    [14.5, y1 - 0.6, 23],
    [9.5, y1 - 0.6, 23],
  ];
  items.push(
    line(
      pathOf(
        window.map((p) => iso(p, P)),
        true,
      ),
      "hi",
    ),
  );
  items.push(solid(cylinder(21.2, y1 - 2, 0.9, 12, 17, P, 10), "mid"));
  items.push(solid(box(6.4, 7.6, y1 - 0.6, y1 + 1.6, 17, 21, 0.3), "lo"));
  // trailer: deck rails, box with ribs, rear doors with lock rods
  const tx0 = 22;
  const tx1 = TRUCK_LENGTH;
  items.push(solid(box(tx0 - 4, tx1, y0 + 1, y1 - 1, 5.5, 8, 0.2), "lo"));
  const ribs: { d: string; tone: LineTone }[] = [];
  for (let x = tx0 + 6; x < tx1 - 2; x += 6)
    ribs.push({ d: segment([x, y1, 8], [x, y1, 30], P), tone: "faint" });
  const doors: { d: string; tone: LineTone }[] = [
    { d: segment([tx1, LANE_Y, 8], [tx1, LANE_Y, 30], P), tone: "lo" },
    {
      d: segment([tx1, LANE_Y - 3.5, 8], [tx1, LANE_Y - 3.5, 30], P),
      tone: "faint",
    },
    {
      d: segment([tx1, LANE_Y + 3.5, 8], [tx1, LANE_Y + 3.5, 30], P),
      tone: "faint",
    },
  ];
  items.push(
    solid(box(tx0, tx1, y0, y1, 8, 30, 0.5, 0.6), "hi", {
      inner: [...ribs, ...doors],
    }),
  );
  items.push(solid(box(tx1 - 1, tx1 + 1.2, y0 + 1, y1 - 1, 4, 6, 0.2), "lo"));
  items.push(
    dots(
      [
        [tx1 + 1.3, y0 + 2, 5],
        [tx1 + 1.3, y1 - 2, 5],
      ],
      "hi",
      0.8,
    ),
  );
  return items;
}
export const TRUCK = truck();
export const TRUCK_HALO = haloOf(
  { x: 0, y: LANE_Y - 7, w: TRUCK_LENGTH, d: 14, r: 3 },
  0,
  2,
  P,
);

/* --------------------------------------------------------------- camera */

let lens: Flat = [0, 0];
function camera(): Item[] {
  const items: Item[] = [];
  const [cx, cy, cz] = RIG;
  const apex: Point3 = [cx, cy, cz + 34];
  const feet: Point3[] = [0, 1, 2].map((k) => {
    const t = (k / 3) * Math.PI * 2 + 0.5;
    return [cx + 15 * Math.cos(t), cy + 15 * Math.sin(t), cz];
  });
  // a weatherproof edge box beside the tripod, cabled to the camera
  const ebox: Plan = { x: cx + 22, y: cy - 4, w: 18, d: 14, r: 1.2 };
  items.push(solid(slab(ebox, cz, cz + 3, 2), "lo"));
  items.push(
    solid(
      slab(
        { x: ebox.x + 1.5, y: ebox.y + 1.5, w: 15, d: 11, r: 1 },
        cz + 3,
        cz + 15,
        2,
        0.6,
      ),
      "mid",
    ),
  );
  const vents: { d: string; tone: LineTone }[] = [];
  for (let k = 0; k < 4; k++) {
    const x = ebox.x + 4 + k * 3;
    vents.push({
      d: segment([x, ebox.y + 12.5, cz + 6], [x, ebox.y + 12.5, cz + 12], P),
      tone: "faint",
    });
  }
  items.push(
    solid(
      slab(
        { x: ebox.x + 3, y: ebox.y + 3, w: 12, d: 8, r: 0.8 },
        cz + 15,
        cz + 16,
        2,
      ),
      "mid",
      { inner: vents },
    ),
  );
  const led = iso([ebox.x + 14, ebox.y + 12.6, cz + 13], P);
  // legs behind the column first
  const ordered = [...feet].sort((a, b) => a[1] - b[1]);
  const legOf = (f: Point3) =>
    solid(beam(f, [apex[0], apex[1], apex[2] - 2], [0, 0, 1], 2, 2, P), "mid");
  const footOf = (f: Point3) =>
    solid(cylinder(f[0], f[1], 2.4, cz, 1.4, P, 14), "lo");
  items.push(
    footOf(ordered[0]!),
    legOf(ordered[0]!),
    footOf(ordered[1]!),
    legOf(ordered[1]!),
  );
  items.push(
    solid(cylinder(cx, cy, 1.6, cz + 14, apex[2] - cz - 14 + 6, P, 14), "mid"),
  );
  items.push(solid(cylinder(cx, cy, 4.4, apex[2] - 2, 3, P, 18), "mid"));
  items.push(footOf(ordered[2]!), legOf(ordered[2]!));
  // pan-tilt head and the camera body aimed at the watched chord
  const head: Point3 = [cx, cy, apex[2] + 4];
  items.push(solid(cylinder(cx, cy, 3, apex[2] + 1, 3, P, 14), "lo"));
  const aim = unit(sub(ROI[0]!, [cx, cy, apex[2] + 9]));
  const back: Point3 = [
    head[0] - aim[0] * 8,
    head[1] - aim[1] * 8,
    head[2] + 5,
  ];
  const front: Point3 = [
    back[0] + aim[0] * 16,
    back[1] + aim[1] * 16,
    back[2] + aim[2] * 16,
  ];
  items.push(solid(beam(back, front, [0, 0, 1], 9, 11, P), "mid"));
  const lensAt = (s: number): Point3 => [
    front[0] + aim[0] * s,
    front[1] + aim[1] * s,
    front[2] + aim[2] * s,
  ];
  items.push(solid(drum(lensAt(4), aim, 3.6, 8, P, 24), "mid"));
  items.push(solid(drum(lensAt(9.5), aim, 4.6, 3, P, 24), "hi"));
  lens = iso(lensAt(11), P);
  const cableFrom = iso([back[0], back[1], back[2] - 2], P);
  const cableTo = iso([ebox.x + 3, ebox.y + 10, cz + 10], P);
  const sag: Flat = [
    (cableFrom[0] + cableTo[0]) / 2,
    Math.max(cableFrom[1], cableTo[1]) + 10,
  ];
  items.push(
    line(
      `M${cableFrom[0].toFixed(1)} ${cableFrom[1].toFixed(1)}Q${sag[0].toFixed(1)} ${sag[1].toFixed(1)} ${cableTo[0].toFixed(1)} ${cableTo[1].toFixed(1)}`,
      "mid",
    ),
  );
  items.push({
    kind: "dots",
    points: [cableFrom, cableTo],
    tone: "hi",
    size: 0.9,
  });
  items.push({ kind: "dots", points: [led], tone: "hi", size: 0.8 });
  return items;
}
// Near-side approach guardrails, drawn after the truck so it passes behind.
export const APPROACH_NEAR: Item[] = [
  ...guardrail(-BANK_X + 10, -7, DECK_HALF + 0.4),
  ...guardrail(SPAN + 7, SPAN + BANK_X - 10, DECK_HALF + 0.4),
];

export const CAMERA = camera();
export const LENS = lens;
export const CAMERA_HALO = haloOf(
  { x: RIG[0] - 14, y: RIG[1] - 12, w: 30, d: 24, r: 10 },
  BANK_TOP,
  1,
  P,
);

/* --------------------------------------------------------------- frames */

export const roiScreen = (dz: number): Flat =>
  iso([ROI[0]![0] - 12, ROI[0]![1], ROI[0]![2] + dz], P);
