// Convex prisms along any axis, shaded by the kit's own rules: the face that
// looks up is the top, the sides fall into four tones by how they face the
// light, the fill and outline are the convex hull.
import {
  cameraOf,
  convexHull,
  iso,
  pathOf,
  SHADES,
  type Flat,
  type Point3,
  type Projection,
  type SolidPaths,
} from "./kit";

export type Vec = Point3;

export const add = (a: Vec, b: Vec): Vec => [
  a[0] + b[0],
  a[1] + b[1],
  a[2] + b[2],
];
export const sub = (a: Vec, b: Vec): Vec => [
  a[0] - b[0],
  a[1] - b[1],
  a[2] - b[2],
];
export const mul = (a: Vec, k: number): Vec => [a[0] * k, a[1] * k, a[2] * k];
export const dot = (a: Vec, b: Vec) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a: Vec, b: Vec): Vec => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
export const unit = (a: Vec): Vec => mul(a, 1 / (Math.hypot(...a) || 1));

/** Direction toward the viewer, matching the kit's depthOf. */
export function viewOf(P: Projection): Vec {
  const { sinA, cosA, sinE, cosE } = cameraOf(P);
  return [cosA * cosE, sinA * cosE, sinE];
}

// Faces whose normals differ by more than this get a crease line.
const CREASE_COS = Math.cos((28 * Math.PI) / 180);

/**
 * Extrude a convex polygon, given as [u, v] in the plane spanned by U and V
 * through `origin`, along the unit axis A for `length`.
 */
export function prism(
  polygon: [number, number][],
  origin: Vec,
  U: Vec,
  V: Vec,
  A: Vec,
  length: number,
  P: Projection,
): SolidPaths {
  const view = viewOf(P);
  const { sinA, cosA } = cameraOf(P);
  const light: Vec = [-sinA, cosA, 0];
  const base = polygon.map(([u, v]) => add(origin, add(mul(U, u), mul(V, v))));
  const cap = base.map((p) => add(p, mul(A, length)));
  const centre = mul(
    base.reduce((s, p) => add(s, p), [0, 0, 0] as Vec),
    1 / base.length,
  );
  type Face = { ring: Vec[]; normal: Vec; edges: string[] };
  const faces: Face[] = [];
  const key = (a: number, b: number) => (a < b ? `${a}:${b}` : `${b}:${a}`);
  const n = base.length;
  faces.push({
    ring: base,
    normal: mul(A, -1),
    edges: base.map((_, i) => key(i, (i + 1) % n)),
  });
  faces.push({
    ring: cap,
    normal: A,
    edges: cap.map((_, i) => key(n + i, n + ((i + 1) % n))),
  });
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    let normal = unit(cross(sub(base[j]!, base[i]!), A));
    const mid = mul(add(base[i]!, base[j]!), 0.5);
    if (dot(normal, sub(mid, centre)) < 0) normal = mul(normal, -1);
    faces.push({
      ring: [base[i]!, base[j]!, cap[j]!, cap[i]!],
      normal,
      edges: [key(i, j), key(j, n + j), key(n + i, n + j), key(i, n + i)],
    });
  }
  const project = (ring: Vec[]): Flat[] => ring.map((p) => iso(p, P));
  const visible = faces.filter((f) => dot(f.normal, view) > 1e-6);
  const tops: string[] = [];
  const buckets: string[][] = Array.from({ length: SHADES }, () => []);
  for (const face of visible) {
    const d = pathOf(project(face.ring), true);
    if (face.normal[2] > 0.55) {
      tops.push(d);
      continue;
    }
    const h = Math.hypot(face.normal[0], face.normal[1]) || 1;
    const lit =
      (dot([face.normal[0] / h, face.normal[1] / h, 0], light) + 1) / 2;
    const shade = Math.min(SHADES - 1, Math.max(0, Math.floor(lit * SHADES)));
    buckets[shade]!.push(d);
  }
  const points = [...base, ...cap];
  const screen = project(points);
  const owners = new Map<string, Vec[]>();
  for (const face of visible)
    for (const edge of face.edges)
      owners.set(edge, [...(owners.get(edge) ?? []), face.normal]);
  const crease: string[] = [];
  for (const [edge, normals] of owners) {
    if (normals.length < 2 || dot(normals[0]!, normals[1]!) > CREASE_COS)
      continue;
    const [a, b] = edge.split(":").map(Number) as [number, number];
    crease.push(pathOf([screen[a]!, screen[b]!]));
  }
  const hull = pathOf(convexHull(screen), true);
  return {
    fill: hull,
    outline: hull,
    crease: crease.join(""),
    top: tops.join(""),
    shades: buckets.map((paths) => paths.join("")),
  };
}

/**
 * A straight member of rectangular section from a to b. `across` is the
 * direction of the section's `width` side; the `depth` side is
 * perpendicular to it and to the member.
 */
export function beam(
  a: Vec,
  b: Vec,
  across: Vec,
  width: number,
  depth: number,
  P: Projection,
): SolidPaths {
  const along = sub(b, a);
  const A = unit(along);
  const U = unit(sub(across, mul(A, dot(across, A))));
  const V = unit(cross(A, U));
  const w = width / 2;
  const h = depth / 2;
  return prism(
    [
      [-w, -h],
      [w, -h],
      [w, h],
      [-w, h],
    ],
    a,
    U,
    V,
    A,
    Math.hypot(...along),
    P,
  );
}

/** A round part on any axis: a wheel, a lens barrel, a pin. */
export function drum(
  centre: Vec,
  axis: Vec,
  radius: number,
  length: number,
  P: Projection,
  steps = 28,
): SolidPaths {
  const A = unit(axis);
  const helper: Vec = Math.abs(A[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0];
  const U = unit(cross(A, helper));
  const V = unit(cross(A, U));
  const ring = Array.from({ length: steps }, (_, i) => {
    const t = (i / steps) * Math.PI * 2;
    return [radius * Math.cos(t), radius * Math.sin(t)] as [number, number];
  });
  return prism(ring, sub(centre, mul(A, length / 2)), U, V, A, length, P);
}

/** A flat plate of any convex outline in the x–z plane, `t` thick along y. */
export function plateXZ(
  outline: [number, number][],
  y: number,
  t: number,
  P: Projection,
): SolidPaths {
  return prism(outline, [0, y, 0], [1, 0, 0], [0, 0, 1], [0, 1, 0], t, P);
}
