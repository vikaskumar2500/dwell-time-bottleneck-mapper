# Implementation roadmap

| Phase | Deliverable | Completion gate | Status |
|---|---|---|---|
| 1. Planning and architecture | Requirements, privacy boundary, HLD, contracts, metrics | Design documents are consistent and reviewable | Complete |
| 2. Spatial analytics foundation | Configuration models, validation, polygon mapping | Unit tests cover valid, invalid, inside, outside, and boundary cases | Complete |
| 3. Dwell analytics MVP | Visits, dwell, heatmap, transitions, bottleneck and dead-zone rules | Deterministic synthetic scenarios match ground truth | Complete |
| 4. YOLO video pipeline | Person detection, tracking, video adapter, annotated output | Recorded-video smoke test and tracker configuration documented | Next |
| 5. Evaluation and portfolio release | Held-out evaluation, CI, demo, measured resume results | Tests pass and results contain no placeholder claims | Planned |
| 6. Product extensions | Dashboard, alert history, calibration, multi-camera research | Defined after baseline evaluation | Future |

## Development workflow

Each phase will be delivered as a focused commit with its acceptance evidence. Later phases will not be presented as complete merely because experimental code exists.

## Data plan

Use consented staged footage or appropriately licensed public tracking data. Evaluation clips should cover sparse and dense traffic, stops, returns, crossing paths, occlusion, carts, groups, and lighting changes. Train, tuning, and test data must be split by recording session rather than neighboring frames.

For ground truth, annotate visible-person points, stable anonymous IDs, and section entry/exit times. Model and threshold decisions use the tuning set; final metrics are calculated once on the held-out test set.

## Main risks

| Risk | Planned mitigation |
|---|---|
| Occlusion and identity switches | Camera placement, tracker tuning, IDF1 and dwell-error analysis |
| Perspective distortion | Floor-plane calibration in a later phase |
| Boundary jitter | Zone hysteresis and explicit boundary tests |
| Noisy bottleneck alerts | Continuous-duration thresholds and recovery logic |
| Privacy concerns | Edge processing and aggregate-only output |
| Misleading business claims | Describe dwell as observed presence and report measured limits |

