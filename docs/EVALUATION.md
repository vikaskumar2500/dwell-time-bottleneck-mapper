# Evaluation

The evaluator compares an analytics `report.json` with ground truth at the business-metric layer. It reports visit-count mean absolute error (MAE), mean-dwell MAE, transition-count MAE, and alert precision, recall, and F1.

## Reproducible baseline

Run the deterministic scenario and score it:

```bash
dwell-map generate-demo
dwell-map analyze
dwell-map evaluate
```

Expected result:

| Metric | Synthetic result |
|---|---:|
| Visit-count MAE | 0.0 |
| Mean-dwell MAE | 0.0 seconds |
| Transition-count MAE | 0.0 |
| Alert precision / recall / F1 | 1.0 / 1.0 / 1.0 |

These values prove that the analytics implementation matches its deterministic fixture. They do not measure detector or tracker accuracy on real shoppers.

## Field evaluation protocol

For a real evaluation, use consented staged footage or appropriately licensed data and split clips by recording session. Annotate each visible person's anonymous track, floor point, zone entry and exit, and expected operational alerts. Tune thresholds on a validation split, then run the final command once on held-out clips.

In addition to the aggregate evaluator, record detection precision and recall, tracking IDF1, identity switches, and floor-position error. Report camera placement, footage duration, crowd density, and hardware with the results so performance claims remain reproducible.

The repository currently provides the evaluation interface and synthetic correctness baseline. Held-out retail footage has not yet been evaluated.
