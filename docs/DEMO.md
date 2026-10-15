# Demo guide

This walkthrough takes about three minutes and uses generated anonymous tracks, so no video or model download is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
dwell-map validate-config config/store.sample.json
dwell-map generate-demo
dwell-map analyze
dwell-map evaluate
```

Open `outputs/demo/zone_metrics.csv` to compare section traffic and dwell time. The generated report identifies the unused promotion zone and the sustained checkout bottleneck. `outputs/demo/heatmap.csv` contains time-weighted occupancy, while `outputs/evaluation.json` records the reproducible correctness metrics.

For the computer-vision path, install `.[video]` and run:

```bash
dwell-map video --source /path/to/store.mp4 --save-video
```

Explain the flow as detection, anonymous tracking, floor-point extraction, zone mapping, temporal aggregation, and operational alerts. Close by noting that the stored analytics contain no faces or persistent identities.
