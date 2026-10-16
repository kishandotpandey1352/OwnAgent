# KV Cache Notes

## What is KV Cache?

KV cache means key-value cache.

In transformer decoding, the model generates text one token at a time. For every new token, the attention layer needs keys and values from previous tokens.

Without KV cache, the model would repeatedly recompute attention information for all previous tokens at every generation step.

With KV cache, the model stores the previously computed key and value tensors and reuses them during generation.

## Why KV Cache Matters

KV cache improves inference speed because the model only needs to compute attention for the new token instead of recomputing all previous tokens.

This is especially important for long prompts and long outputs.

## Example

If a prompt has 1,000 tokens and the model generates 100 new tokens:

- Without KV cache, previous token attention is repeatedly recomputed.
- With KV cache, previous key/value tensors are reused.

This reduces repeated computation and improves token generation speed.

## Tradeoff

KV cache improves speed but uses GPU memory.

Longer prompts, longer generations, and more concurrent users all increase KV cache memory usage.

## KV Cache in vLLM

vLLM improves KV cache memory management using PagedAttention.

PagedAttention stores KV cache in memory blocks, similar to how operating systems manage virtual memory pages. This reduces memory fragmentation and allows vLLM to serve more concurrent requests efficiently.

## Why This Matters for This Project

This finance AI platform needs efficient inference because users may submit long financial documents, SEC filing chunks, earnings call excerpts, or risk-analysis inputs.

Efficient KV cache management helps the system:

- reduce latency
- improve throughput
- support longer inputs
- serve multiple requests more efficiently

## Summary

KV cache makes autoregressive generation faster by reusing previous attention states. vLLM builds on this with PagedAttention, which manages KV cache memory more efficiently for production-style serving.