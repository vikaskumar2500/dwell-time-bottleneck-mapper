# Requirements and scope

## Users

- Store managers reviewing customer flow and congestion
- Operations analysts comparing layouts and promotions
- ML engineers configuring and validating camera pipelines

## Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | Configure named polygonal sections without code changes |
| FR-02 | Detect and track people using temporary session-local IDs |
| FR-03 | Record section entry, exit, re-entry, and journey transitions |
| FR-04 | Calculate per-visit and aggregate section dwell time |
| FR-05 | Generate time-weighted spatial heatmaps |
| FR-06 | Detect sustained high-occupancy bottlenecks |
| FR-07 | Detect sections with traffic below a configurable threshold |
| FR-08 | Export zone metrics, transitions, and alerts as JSON and CSV |
| FR-09 | Support recorded video and live camera sources |

## Quality requirements

- The analytics core must run independently of the vision model.
- Invalid configuration must fail before video processing begins.
- Performance claims must name the hardware, resolution, FPS, and crowd density.
- Evaluation data must be separated by recording session.
- No face recognition, biometric templates, or demographic classification.

## Metric definitions

- **Dwell time:** observed time inside a configured section; it does not prove attention or purchase intent.
- **Journey:** ordered sequence of section visits within one camera session.
- **Bottleneck:** occupancy at or above a threshold for a continuous minimum duration.
- **Dead zone:** section at or below a visit threshold during a defined analysis window.
- **Heat:** tracked presence time accumulated in spatial grid cells.

## Baseline scope

The first working release targets one fixed camera, person tracking, image-coordinate zones, session-local identity, and aggregate reports. Multi-camera association, customer demographics, purchase attribution, and revenue-impact claims are outside the baseline.

