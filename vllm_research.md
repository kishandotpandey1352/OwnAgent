# vLLM Research Notes

## What is vLLM?

High-performance LLM inference engine.

Benefits:
- Fast serving
- Efficient memory usage
- Dynamic batching

---

## Continuous Batching

Allows requests arriving at different times
to join active batches.

Benefits:
- Better GPU utilization
- Higher throughput

---

## KV Cache

Stores attention keys and values from
previous tokens.

Benefits:
- Faster token generation

---

## Paged Attention

Uses virtual-memory style paging
for KV cache.

Benefits:
- Reduced fragmentation
- Lower memory consumption
- More concurrent requests

---

## Why We Will Use It

Week 3:
- Deploy finance model
- Measure latency
- Measure throughput
- Compare batch sizes