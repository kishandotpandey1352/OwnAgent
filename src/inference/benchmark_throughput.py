import argparse
import concurrent.futures
import json
import time
import urllib.request


PROMPTS = [
    "Summarize this financial update: Revenue increased by 18 percent, but operating expenses also rose due to higher cloud infrastructure costs.",
    "Identify the main financial risk: The company depends on a small number of enterprise customers for most of its revenue.",
    "Answer the question: What does rising operating margin usually indicate about a company's profitability?",
    "Summarize this earnings note: Net income improved due to higher gross margin and disciplined cost management.",
    "Identify the risk: The company may face liquidity pressure if refinancing conditions worsen.",
]


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

    with urllib.request.urlopen(request, timeout=240) as response:
        result = json.loads(response.read().decode("utf-8"))

    end = time.perf_counter()

    usage = result.get("usage", {})

    return {
        "latency_seconds": end - start,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "response": result["choices"][0]["message"]["content"],
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark vLLM throughput.")

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
        default=20,
        help="Total number of requests to send",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of concurrent requests",
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
        default="reports/throughput_benchmark_day12.json",
        help="Output JSON report",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("vLLM Throughput Benchmark")
    print("=" * 80)
    print(f"Base URL: {args.base_url}")
    print(f"Model: {args.model}")
    print(f"Total requests: {args.num_requests}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Max tokens: {args.max_tokens}")
    print()

    prompts = [PROMPTS[i % len(PROMPTS)] for i in range(args.num_requests)]

    start_time = time.perf_counter()

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                call_vllm,
                args.base_url,
                args.model,
                prompt,
                args.max_tokens,
                args.temperature,
            )
            for prompt in prompts
        ]

        for i, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            result = future.result()
            results.append(result)

            print(
                f"Completed {i}/{args.num_requests} | "
                f"Latency: {result['latency_seconds']:.3f}s | "
                f"Total tokens: {result['total_tokens']}"
            )

    end_time = time.perf_counter()

    total_time = end_time - start_time
    total_tokens = sum(r["total_tokens"] for r in results)
    completion_tokens = sum(r["completion_tokens"] for r in results)

    summary = {
        "model": args.model,
        "base_url": args.base_url,
        "num_requests": args.num_requests,
        "concurrency": args.concurrency,
        "max_tokens": args.max_tokens,
        "total_time_seconds": total_time,
        "requests_per_second": args.num_requests / total_time,
        "total_tokens": total_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens_per_second": total_tokens / total_time,
        "completion_tokens_per_second": completion_tokens / total_time,
        "individual_results": results,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 80)
    print("Throughput Summary")
    print("=" * 80)
    print(f"Total time: {total_time:.3f}s")
    print(f"Requests/sec: {summary['requests_per_second']:.3f}")
    print(f"Total tokens/sec: {summary['total_tokens_per_second']:.3f}")
    print(f"Completion tokens/sec: {summary['completion_tokens_per_second']:.3f}")
    print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()

