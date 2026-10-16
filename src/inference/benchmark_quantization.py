import argparse
import json
import statistics
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def percentile(values, percent):
    values = sorted(values)
    index = int((percent / 100) * (len(values) - 1))
    return values[index]


def get_quantization_config(quantization: str):
    if quantization == "fp16":
        return None

    if quantization == "int8":
        return BitsAndBytesConfig(
            load_in_8bit=True,
        )

    if quantization == "int4":
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

    raise ValueError("quantization must be one of: fp16, int8, int4")


def load_model(model_name: str, quantization: str):
    print("=" * 80)
    print("Loading model")
    print("=" * 80)
    print(f"Model: {model_name}")
    print(f"Quantization: {quantization}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = get_quantization_config(quantization)

    load_start = time.perf_counter()

    if quantization == "fp16":
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
        )

    load_end = time.perf_counter()

    model.eval()

    load_time = load_end - load_start

    print(f"Model loaded in {load_time:.2f}s")

    return model, tokenizer, load_time


def format_prompt(tokenizer, user_prompt: str):
    messages = [
        {
            "role": "user",
            "content": user_prompt,
        }
    ]

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    return f"""### Instruction:
{user_prompt}

### Response:
"""


def generate_once(model, tokenizer, prompt: str, max_new_tokens: int):
    formatted_prompt = format_prompt(tokenizer, prompt)

    inputs = tokenizer(
        formatted_prompt,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(model.device)
        for key, value in inputs.items()
    }

    if torch.cuda.is_available():
        torch.cuda.synchronize()

    start = time.perf_counter()

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    if torch.cuda.is_available():
        torch.cuda.synchronize()

    end = time.perf_counter()

    input_tokens = inputs["input_ids"].shape[-1]
    output_tokens = output_ids.shape[-1]
    completion_tokens = output_tokens - input_tokens

    generated_ids = output_ids[0][input_tokens:]
    generated_text = tokenizer.decode(
        generated_ids,
        skip_special_tokens=True,
    ).strip()

    latency = end - start

    return {
        "latency_seconds": latency,
        "prompt_tokens": input_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": output_tokens,
        "completion_tokens_per_second": completion_tokens / latency if latency > 0 else 0,
        "response": generated_text,
    }


def cuda_memory_summary():
    if not torch.cuda.is_available():
        return {
            "cuda_available": False,
            "allocated_gb": None,
            "reserved_gb": None,
            "max_allocated_gb": None,
            "max_reserved_gb": None,
        }

    return {
        "cuda_available": True,
        "allocated_gb": torch.cuda.memory_allocated() / 1024**3,
        "reserved_gb": torch.cuda.memory_reserved() / 1024**3,
        "max_allocated_gb": torch.cuda.max_memory_allocated() / 1024**3,
        "max_reserved_gb": torch.cuda.max_memory_reserved() / 1024**3,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark FP16, INT8, and INT4 model inference."
    )

    parser.add_argument(
        "--model-name",
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Model name or local path",
    )

    parser.add_argument(
        "--quantization",
        choices=["fp16", "int8", "int4"],
        required=True,
        help="Quantization mode",
    )

    parser.add_argument(
        "--num-requests",
        type=int,
        default=5,
        help="Number of generation requests",
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=128,
        help="Maximum new tokens to generate",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON report path",
    )

    args = parser.parse_args()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    prompt = (
        "Summarize this financial update clearly and concisely: "
        "Revenue increased by 18 percent due to stronger enterprise demand, "
        "but operating expenses also rose because of higher cloud infrastructure "
        "and employee compensation costs."
    )

    model, tokenizer, load_time = load_model(
        model_name=args.model_name,
        quantization=args.quantization,
    )

    results = []

    print()
    print("=" * 80)
    print("Running benchmark")
    print("=" * 80)

    for i in range(args.num_requests):
        result = generate_once(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt,
            max_new_tokens=args.max_new_tokens,
        )

        results.append(result)

        print(
            f"Request {i + 1}/{args.num_requests} | "
            f"Latency: {result['latency_seconds']:.3f}s | "
            f"Completion tokens/sec: {result['completion_tokens_per_second']:.3f}"
        )

    latencies = [r["latency_seconds"] for r in results]
    completion_tps = [r["completion_tokens_per_second"] for r in results]
    completion_tokens = [r["completion_tokens"] for r in results]
    total_tokens = [r["total_tokens"] for r in results]

    report = {
        "model_name": args.model_name,
        "quantization": args.quantization,
        "num_requests": args.num_requests,
        "max_new_tokens": args.max_new_tokens,
        "load_time_seconds": load_time,
        "latency_seconds": {
            "min": min(latencies),
            "max": max(latencies),
            "mean": statistics.mean(latencies),
            "p50": statistics.median(latencies),
            "p95": percentile(latencies, 95),
        },
        "tokens": {
            "total_completion_tokens": sum(completion_tokens),
            "total_tokens": sum(total_tokens),
            "average_completion_tokens": statistics.mean(completion_tokens),
            "average_total_tokens": statistics.mean(total_tokens),
            "mean_completion_tokens_per_second": statistics.mean(completion_tps),
        },
        "memory": cuda_memory_summary(),
        "individual_results": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 80)
    print("Benchmark Summary")
    print("=" * 80)
    print(f"Quantization: {args.quantization}")
    print(f"Mean latency: {report['latency_seconds']['mean']:.3f}s")
    print(f"P50 latency: {report['latency_seconds']['p50']:.3f}s")
    print(f"P95 latency: {report['latency_seconds']['p95']:.3f}s")
    print(
        "Mean completion tokens/sec: "
        f"{report['tokens']['mean_completion_tokens_per_second']:.3f}"
    )
    print(f"CUDA memory: {report['memory']}")
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()