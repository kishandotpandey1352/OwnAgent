import argparse
import json
import statistics
import time
import urllib.request


def call_vllm(base_url: str, model: str, prompt: str, max_tokens: int, temperature: float):
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    end = time.perf_counter()

    latency_seconds = end - start
    usage = result.get("usage", {})

    return {
        "latency_seconds": latency_seconds,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "response": result["choices"][0]["message"]["content"],
    }


def percentile(values, percent):
    values = sorted(values)
    index = int((percent / 100) * (len(values) - 1))
    return values[index]


def main():
    parser = argparse.ArgumentParser(description="Benchmark vLLM latency.")

    parser.add_argument(
        "--base-url",
        default="http://localhost:8001",
        help="vLLM base URL",
    )

    parser.add_argument(
        "--model",
        default="finance-qwen1.5b",
        help="Served model name",
    )

    parser.add_argument(
        "--num-requests",
        type=int,
        default=10,
        help="Number of requests to send",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=128,
        help="Maximum generated tokens",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature",
    )

    parser.add_argument(
        "--output",
        default="reports/latency_benchmark_day12.json",
        help="Output JSON report",
    )

    args = parser.parse_args()

    prompt = (
        "Summarize this financial update: Revenue increased by 18 percent, "
        "but operating expenses also rose due to higher cloud infrastructure costs."
    )

    results = []

    print("=" * 80)
    print("vLLM Latency Benchmark")
    print("=" * 80)
    print(f"Base URL: {args.base_url}")
    print(f"Model: {args.model}")
    print(f"Requests: {args.num_requests}")
    print(f"Max tokens: {args.max_tokens}")
    print()

    for i in range(args.num_requests):
        result = call_vllm(
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

        results.append(result)

        print(
            f"Request {i + 1}/{args.num_requests} | "
            f"Latency: {result['latency_seconds']:.3f}s | "
            f"Total tokens: {result['total_tokens']}"
        )

    latencies = [r["latency_seconds"] for r in results]
    total_tokens = [r["total_tokens"] for r in results]
    completion_tokens = [r["completion_tokens"] for r in results]

    summary = {
        "model": args.model,
        "base_url": args.base_url,
        "num_requests": args.num_requests,
        "max_tokens": args.max_tokens,
        "latency_seconds": {
            "min": min(latencies),
            "max": max(latencies),
            "mean": statistics.mean(latencies),
            "median_p50": statistics.median(latencies),
            "p95": percentile(latencies, 95),
        },
        "tokens": {
            "total_tokens": sum(total_tokens),
            "completion_tokens": sum(completion_tokens),
            "average_total_tokens_per_request": statistics.mean(total_tokens),
            "average_completion_tokens_per_request": statistics.mean(completion_tokens),
        },
        "individual_results": results,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 80)
    print("Latency Summary")
    print("=" * 80)
    print(f"Mean latency: {summary['latency_seconds']['mean']:.3f}s")
    print(f"P50 latency: {summary['latency_seconds']['median_p50']:.3f}s")
    print(f"P95 latency: {summary['latency_seconds']['p95']:.3f}s")
    print(f"Min latency: {summary['latency_seconds']['min']:.3f}s")
    print(f"Max latency: {summary['latency_seconds']['max']:.3f}s")
    print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()

