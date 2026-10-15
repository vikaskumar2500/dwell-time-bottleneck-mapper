# Resume notes

## Suggested project entry

**Dwell-Time & Bottleneck Mapper — Python, YOLO11, ByteTrack, OpenCV**

- Built a privacy-aware retail vision pipeline that converts camera feeds into anonymous tracks, zone-level dwell metrics, traffic heatmaps, journey transitions, and bottleneck or dead-zone alerts.
- Designed a model-independent observation interface and configurable polygon analytics engine with JSON, CSV, image, and optional annotated-video outputs.
- Added deterministic business-metric evaluation, automated tests, and GitHub Actions across Python 3.9 and 3.12; the synthetic baseline reproduces expected visits, dwell times, transitions, and alerts exactly.

Use measured field results only after following the held-out protocol in [EVALUATION.md](EVALUATION.md). Do not turn the synthetic result into a claim about accuracy on real shoppers.
