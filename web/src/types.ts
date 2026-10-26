export type Status = "NORMAL" | "WATCH" | "ALERT" | "INSUFFICIENT_EVIDENCE";
export interface Roi {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}
export interface Bridge {
  bridge: {
    id: string;
    name: string;
    band: { low_hz: number; high_hz: number };
    rois: Roi[];
  };
  synthetic: boolean;
  sampling_multiplier: number;
}
export interface Trace {
  ts: string;
  state: string;
  decision: string;
  action: string;
  outcome: string;
  evidence: Record<string, string | number | boolean | null>;
  proposal: string | null;
}
export interface Series {
  time_seconds: number[];
  displacement_px: number[];
  displacement_mm: number[] | null;
  method: string;
  roi_id: string;
  fps: number;
}
export interface Spectrum {
  frequency_hz: number[];
  psd_px2_per_hz: number[];
  peak_hz: number;
  snr_db: number;
  amplitude_rms_px: number;
  resolution_hz: number;
}
export interface Estimate {
  outcome: string;
  reasons: string[];
  selected: Series | null;
  spectrum: Spectrum | null;
  ci_hz: [number, number] | null;
  stabilization_applied: boolean;
  provenance: { cv2_version: string; cool_verified: boolean };
  roi_estimates: { series: Series; spectrum: Spectrum }[];
}
export interface CaptureRecord {
  capture: {
    id: string;
    bridge_id: string;
    temperature_c: number | null;
    rois: Roi[];
  };
  created_at: string;
  status: string;
  error: string | null;
  synthetic: boolean;
  artifacts: string[];
  result: {
    estimate: Estimate | null;
    decision: {
      status: Status;
      reason: string;
      action: string;
      approval_id: string | null;
    };
    trace: Trace[];
    sampling_multiplier: number;
  } | null;
}
export interface Approval {
  id: string;
  bridge_id: string;
  capture_id: string;
  status: string;
  reason: string;
  delivery: string;
  created_at: string;
}
export type Evidence = Record<string, unknown>;
