// The one model that moves the figure: a simply supported span vibrating in
// its first bending mode, loaded by the axles of a truck that crosses it.
// Units are drawing units, and time is slowed so the motion can be followed.
// Nothing here is a measurement.

export const SPAN = 360;
export const PANELS = 8;
export const PANEL = SPAN / PANELS;
export const TRUCK_LENGTH = 74;
/** Route from where the truck appears to where it leaves, by its front bumper,
 * measured along its direction of travel from the far end of the span. */
export const ROAD: [number, number] = [-40, SPAN + 40 + TRUCK_LENGTH];
const SPEED = 92; // drawing units per second
const MODE_HZ = 0.95; // slowed for the eye
const DAMPING = 0.035; // ratio of critical
const SAG = 4.2; // midspan sag under the whole truck, exaggerated
const PAUSE = 4.5; // seconds between trucks on the idle tour
const AXLES = [
  { at: -9, share: 0.18 },
  { at: -25, share: 0.41 },
  { at: -66, share: 0.41 },
];

/** First mode shape of a simply supported span. */
export const shape = (x: number) =>
  x <= 0 || x >= SPAN ? 0 : Math.sin((Math.PI * x) / SPAN);

export type BridgeState = {
  q: number; // modal amplitude, negative is down
  rate: number;
  front: number | null; // truck front bumper, null when no truck
  wait: number; // seconds until the next truck on the idle tour
};

export const restState = (): BridgeState => ({
  q: 0,
  rate: 0,
  front: null,
  wait: 1.2,
});

/** Modal force of the truck at this position, as a static sag. */
function load(front: number | null) {
  if (front === null) return 0;
  return -SAG * AXLES.reduce((s, a) => s + a.share * shape(front + a.at), 0);
}

/** Static pose with the truck parked at `front`, for still figures. */
export function parked(front: number | null): BridgeState {
  return { ...restState(), front, q: load(front) };
}

export function step(state: BridgeState, dt: number, tour: boolean) {
  if (state.front === null) {
    if (tour) state.wait -= dt;
    if (state.wait <= 0) launch(state);
  } else {
    state.front += SPEED * dt;
    if (state.front > ROAD[1]) {
      state.front = null;
      state.wait = PAUSE;
    }
  }
  const w = 2 * Math.PI * MODE_HZ;
  const target = load(state.front);
  const steps = Math.max(1, Math.ceil(dt * 240));
  const h = dt / steps;
  for (let i = 0; i < steps; i++) {
    const accel = -2 * DAMPING * w * state.rate - w * w * (state.q - target);
    state.rate += accel * h;
    state.q += state.rate * h;
  }
  return (
    state.front !== null ||
    Math.abs(state.q) > 0.004 ||
    Math.abs(state.rate) > 0.004
  );
}

export function launch(state: BridgeState) {
  if (state.front === null) state.front = ROAD[0];
}

function onSpan(front: number | null) {
  return front !== null && front > 0 && front - TRUCK_LENGTH < SPAN;
}

/** Vertical deflection of the deck at x. */
export const deflection = (state: BridgeState, x: number) => state.q * shape(x);

/** Fade the truck in and out at the ends of the drawn road. */
export function truckOpacity(front: number) {
  const fade = 40;
  const a = Math.min(1, (front - ROAD[0]) / fade);
  const b = Math.min(1, (ROAD[1] - front) / fade);
  return Math.max(0, Math.min(a, b));
}

export function readout(state: BridgeState) {
  const { front } = state;
  if (front !== null && front <= 0) return "Truck approaching";
  if (front !== null && onSpan(front)) {
    const across = Math.min(1, Math.max(0, (front - TRUCK_LENGTH / 2) / SPAN));
    return `Truck on span, ${Math.round(across * 100)}% across`;
  }
  if (Math.abs(state.q) > 0.05 || Math.abs(state.rate) > 0.2)
    return "Free vibration, ringing down";
  return "At rest";
}
