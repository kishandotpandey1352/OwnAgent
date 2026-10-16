# Inference Benchmark Report

## 1. Goal

The goal of this report is to summarize inference performance for the finance AI platform. The benchmark focuses on latency, throughput, quantization, and GPU memory tradeoffs.

## 2. Serving Setup

| Item | Value |
|---|---|
| Local serving engine | vLLM |
| vLLM served model | `finance-qwen1.5b` |
| vLLM base model | `Qwen/Qwen2.5-1.5B-Instruct` |
| Quantization benchmark model | `Qwen/Qwen2.5-3B-Instruct` |
| Quantization runtime | Transformers + bitsandbytes |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |
| VRAM | ~8GB |
| API format | OpenAI-compatible API |

## 3. Batch Size / Concurrency vs Throughput

In this local vLLM benchmark, concurrency is used as the practical serving equivalent of batch pressure. Higher concurrency means multiple requests are sent to the server at the same time.

| Run | Concurrency | Requests | Max Tokens | Total Time (s) | Requests/sec | Total Tokens/sec | Completion Tokens/sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| c1 | 1 | 20 | 128 | 26.137 | 0.765 | 104.373 | 66.113 |
| c2 | 2 | 20 | 128 | 14.659 | 1.364 | 186.435 | 118.219 |
| c4 | 4 | 20 | 128 | 8.665 | 2.308 | 314.957 | 199.546 |

## 4. Generation Length vs Latency

This table shows how latency changes as the maximum generation length increases. Longer generations usually increase latency because the model must decode more tokens.

| Run | Max Tokens | Requests | Mean Latency (s) | P50 Latency (s) | P95 Latency (s) | Min (s) | Max (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| t64 | 64 | 10 | 0.574 | 0.469 | 0.851 | 0.417 | 0.947 |
| t128 | 128 | 10 | 0.467 | 0.476 | 0.524 | 0.401 | 0.541 |
| t256 | 256 | 10 | 0.543 | 0.441 | 0.693 | 0.416 | 0.974 |

## 5. INT4 vs FP16 Quantization

This table compares different model loading modes for `Qwen/Qwen2.5-3B-Instruct` using Transformers and bitsandbytes. The purpose is to understand the tradeoff between speed and memory usage.

| Run | Quantization | Requests | Max New Tokens | Load Time (s) | Mean Latency (s) | P50 (s) | P95 (s) | Completion Tokens/sec | Max Allocated VRAM (GB) | Max Reserved VRAM (GB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FP16 | fp16 | 5 | 128 | 4.413 | 1.497 | 1.229 | 1.233 | 24.947 | 5.787 | 5.824 |
| INT8 | int8 | 5 | 128 | 18.748 | 5.507 | 5.013 | 5.021 | 6.352 | 3.245 | 3.318 |
| INT4 | int4 | 5 | 128 | 7.317 | 2.518 | 2.213 | 2.320 | 15.728 | 2.047 | 2.070 |

## 6. Memory vs Latency

This table focuses specifically on the relationship between GPU memory usage and response latency. Lower memory usage is useful for limited VRAM, but it does not always mean faster inference.

| Run | Quantization | Max Allocated VRAM (GB) | Mean Latency (s) | Completion Tokens/sec |
|---|---|---:|---:|---:|
| FP16 | fp16 | 5.787 | 1.497 | 24.947 |
| INT8 | int8 | 3.245 | 5.507 | 6.352 |
| INT4 | int4 | 2.047 | 2.518 | 15.728 |

## 7. Interpretation

### Batch Size / Concurrency vs Throughput

Increasing concurrency can improve throughput because vLLM can process multiple requests together. However, if concurrency becomes too high for the local GPU, individual latency may increase or throughput may stop improving.

### INT4 vs FP16

FP16 usually provides the fastest inference when the model fits comfortably in GPU memory. INT4 uses much less VRAM, which makes it useful for running larger models on limited hardware. In this project, INT4 allowed Qwen2.5-3B-Instruct to run with much lower memory usage than FP16.

### Memory vs Latency

Lower memory usage does not always mean lower latency. Quantized inference can be slower or faster depending on kernel support, GPU architecture, and runtime implementation. The practical choice depends on whether the priority is speed, memory efficiency, or serving stability.

## 8. Final Conclusion

The inference benchmarks show that the local platform can serve models through vLLM and can also run the larger Qwen2.5-3B-Instruct model using quantized Transformers inference. For reliable local vLLM serving, `finance-qwen1.5b` is the practical model. For memory-efficient local inference with the larger 3B model, INT4 is the most practical option.
