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
    span_type: "cantilever" | "simply_supported" | "unknown";
    span_length_m: number | null;
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
  fdd: Fdd | null;
}
export interface Fdd {
  roi_ids: string[];
  frequency_hz: number[];
  principal_psd: number[];
  peak_bin_hz: number;
  mode_shape_real: number[];
  mode_shape_imag: number[];
}
export interface Baseline {
  bridge_id: string;
  f0_hz: number;
  temperature_reference_c: number;
  alpha_per_c: number;
  residual_std_hz: number;
  capture_ids: string[];
  temperature_min_c: number;
  temperature_max_c: number;
}
export interface CaptureRecord {
  capture: {
    id: string;
    bridge_id: string;
    temperature_c: number | null;
    rois: Roi[];
    stabilize?: boolean;
    trigger_source?: "operator_upload" | "heavy_vehicle_exit" | "motion_energy";
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
  resolved_at: string | null;
}
export interface Health {
  status: string;
  transport: string;
  planner: string;
  cloud_deployed: boolean;
  admin_configured: boolean;
  stabilization_ready: boolean;
  vehicle_detection_ready: boolean;
}
export interface DeskResult {
  kind: string;
  synthetic?: boolean;
  captures: {
    capture_id: string;
    state: string;
    accelerometer_hz: number;
    accelerometer_sample_rate: number;
    video_hz: number | null;
    frequency_error_percent: number | null;
    outcome: string;
    reasons: string[];
  }[];
  limitations: string[];
}
export type Evidence = Record<string, unknown>;
