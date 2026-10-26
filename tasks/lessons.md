# Engineering lessons

- Keep acquisition timing separate from playback timestamps. Container clock quantization can resemble dropped frames; actual timing gaps must still be rejected.
- Change the bootstrap window together with the spectral window when retrying a measurement.
- A historical frequency drop cannot confirm an alert when its uncertainty still overlaps the healthy prediction interval.
- Compare parallel ROI execution against its startup and serialization overhead before enabling it by default.
- Consume WebSocket disconnect events so idle live connections cannot hold server shutdown open.
- Plan every operator-drawn ROI. Planning only the first one silently hides per-region estimates and the FDD mode shape.
- Keep the selected bridge and capture in the route. A selection held only in memory resets on reload, and protected actions can then apply to the wrong bridge.
