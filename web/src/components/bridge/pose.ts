// Turns the model's deflection into screen transforms. Each panel group is
// sheared so that every point moves down by the deflection at its own x,
// interpolated straight between the panel's two nodes, the way a truss
// panel's straight members follow its joints.
import { cameraOf, translateAlong } from "../iso/kit";
import { P, type Plane } from "./geometry";
import {
  deflection,
  PANEL,
  PANELS,
  SPAN,
  TRUCK_LENGTH,
  type BridgeState,
} from "./model";

const { sinA, cosA, sinE, cosE, k } = cameraOf(P);
const [ox, oy] = P.origin;

/** World x of a screen point lying in `plane`, as ax·sx + ay·sy + a0. */
function inverse(plane: Plane): [number, number, number] {
  if ("vertical" in plane) {
    const y = plane.vertical;
    return [1 / (sinA * k), 0, (-ox + y * cosA * k) / (sinA * k)];
  }
  const z = plane.horizontal;
  return [
    sinA / k,
    cosA / (k * sinE),
    (-ox * sinA) / k + (cosA * (-oy / k + z * cosE)) / sinE,
  ];
}

export function panelTransforms(state: BridgeState, plane: Plane): string[] {
  const [ax, ay, a0] = inverse(plane);
  const nodes = Array.from({ length: PANELS + 1 }, (_, i) =>
    deflection(state, i * PANEL),
  );
  return Array.from({ length: PANELS }, (_, i) => {
    const d0 = nodes[i]!;
    const slope = (nodes[i + 1]! - d0) / PANEL;
    const s = -cosE * k;
    const b = s * slope * ax;
    const c = s * slope * ay;
    const f = s * (d0 + slope * (a0 - i * PANEL));
    return `matrix(1 ${b.toFixed(5)} 0 ${(1 + c).toFixed(5)} 0 ${f.toFixed(3)})`;
  });
}

/**
 * The model measures the truck along its route; it drives toward −x, so the
 * route runs backward over the span. The mode shape is symmetric, so the
 * load the model computes is the same either way.
 */
export function truckTransform(state: BridgeState, front: number) {
  const x = SPAN - front;
  return translateAlong(P, [x, 0, deflection(state, x + TRUCK_LENGTH / 2)]);
}
