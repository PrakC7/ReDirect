# Government Evaluation Notes

## Alignment with Delhi Constraints
- Uses existing CCTV/traffic cameras with frame skipping and edge inference.
- Supports mixed traffic types including two-wheelers and buses.
- Minimal bandwidth usage by sending only counts and metadata.
- Works with low-cost edge devices such as Raspberry Pi or Jetson Nano.

## Cost Effectiveness
- Lightweight YOLOv8 model and selective inference.
- Single regional backend for multiple intersections.
- Open-source stack with low operational cost.

## Reliability and Latency
- Edge-first detection reduces latency.
- Batch processing lowers compute load.
- Asynchronous ingestion avoids blocking on API calls.

## Emergency Handling
- Vision detection of emergency vehicles.
- Emergency portal allows manual override with severity levels.
- Sequential corridor signal planning.

## Scalability Roadmap
- Add zones for regional optimization.
- Introduce city command layer with policy rules.
- Integrate existing control room workflows.
