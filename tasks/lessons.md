# Engineering lessons

- Keep acquisition timing separate from playback timestamps. Container clock quantization can resemble dropped frames; actual timing gaps must still be rejected.
- Change the bootstrap window together with the spectral window when retrying a measurement.
- A historical frequency drop cannot confirm an alert when its uncertainty still overlaps the healthy prediction interval.
- Compare parallel ROI execution against its startup and serialization overhead before enabling it by default.
- Consume WebSocket disconnect events so idle live connections cannot hold server shutdown open.
