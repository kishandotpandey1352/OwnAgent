# Day 14 Quantization Comparison

## Goal

The goal of Day 14 was to compare INT8 and INT4 quantized inference for the finance model serving pipeline.

## Setup

| Item | Value |
|---|---|
| Model | `Qwen/Qwen2.5-3B-Instruct` |
| Runtime | Transformers + bitsandbytes |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |
| VRAM | ~8GB |
| Task | Financial summarization prompt |

## Results

| Run | Quantization | Requests | Max New Tokens | Load Time (s) | Mean Latency (s) | P50 (s) | P95 (s) | Completion Tokens/sec | Max Allocated VRAM (GB) | Max Reserved VRAM (GB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FP16 | fp16 | 5 | 128 | 4.413 | 1.497 | 1.229 | 1.233 | 24.947 | 5.787 | 5.824 |
| INT8 | int8 | 5 | 128 | 18.748 | 5.507 | 5.013 | 5.021 | 6.352 | 3.245 | 3.318 |
| INT4 | int4 | 5 | 128 | 7.317 | 2.518 | 2.213 | 2.320 | 15.728 | 2.047 | 2.070 |

## Interpretation

INT8 quantization reduces model memory compared with FP16 while usually preserving more numerical precision than INT4. INT4 quantization reduces memory further, which can make larger models practical on limited VRAM, but it may affect output quality or latency depending on kernels and hardware.

For this local setup, the key question is whether INT8 or INT4 allows Qwen2.5-3B-Instruct to run comfortably on the RTX 5060 Laptop GPU while maintaining acceptable latency and output quality.

## Notes

Day 14 uses Transformers + bitsandbytes for quantization benchmarking. vLLM serving remains available for the smaller `finance-qwen1.5b` model, while quantization experiments are used to understand memory tradeoffs for the larger Qwen2.5-3B model.

## Day 14 Summary

Day 14 tested INT8 and INT4 quantized inference for Qwen2.5-3B-Instruct using Transformers and bitsandbytes.

The purpose was to understand whether quantization can reduce GPU memory usage enough to make larger model inference more practical on the local RTX 5060 Laptop GPU with approximately 8GB VRAM.

INT8 was used as the higher-precision quantized option, while INT4 was used as the more memory-efficient option. The results will guide later serving decisions, especially when deciding whether to serve a smaller FP16 model through vLLM or a larger quantized model through a different inference path.