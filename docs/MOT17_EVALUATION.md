# MOT17 evaluation

Phase 6 uses an existing annotated pedestrian-tracking dataset instead of locally recorded footage. MOT17 provides image sequences, person bounding boxes, and stable ground-truth identities. The adapter converts each ground-truth box to the same bottom-center observation contract used by YOLO and ByteTrack.

MOT17 is distributed for non-commercial research under CC BY-NC-SA 3.0. Download it from the [MOTChallenge dataset page](https://motchallenge.net/data/MOT17/) and retain its original license and attribution. Dataset images, annotations, converted videos, and model weights are ignored by Git and must not be committed to this repository.

## Prepare one sequence

After extracting the MOT17 training set, choose one sequence directory containing `seqinfo.ini`, `img1/`, and `gt/gt.txt`:

```bash
dwell-map prepare-mot \
  --sequence data/external/MOT17/train/MOT17-04-SDP \
  --output data/processed/MOT17-04-SDP \
  --video
```

This produces:

- `store.json`: three reproducible left, center, and right image-space zones
- `ground_truth.jsonl`: official person IDs converted to bottom-center observations
- `sequence.mp4`: source frames assembled for the existing video pipeline
- `manifest.json`: sequence and conversion counts

## Produce comparable reports

First create the ground-truth business report:

```bash
dwell-map analyze \
  --config data/processed/MOT17-04-SDP/store.json \
  --input data/processed/MOT17-04-SDP/ground_truth.jsonl \
  --output outputs/mot17/ground-truth
```

Run YOLO and ByteTrack on the same pixels and zones:

```bash
dwell-map video \
  --source data/processed/MOT17-04-SDP/sequence.mp4 \
  --config data/processed/MOT17-04-SDP/store.json \
  --output outputs/mot17/predicted
```

Compare aggregate business metrics:

```bash
dwell-map evaluate \
  --report outputs/mot17/predicted/report.json \
  --ground-truth outputs/mot17/ground-truth/report.json \
  --output outputs/mot17/evaluation.json
```

MOT17 is a pedestrian-surveillance benchmark rather than an in-store dataset. Results measure the technical tracking-to-analytics pipeline and should not be described as retail deployment accuracy.
