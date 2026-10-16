import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


QA_PAYLOADS = [
    {
        "question": "Why did operating margin decline?",
        "context": (
            "Revenue increased by 18 percent due to stronger enterprise demand. "
            "However, operating expenses increased because of higher cloud infrastructure "
            "costs and employee compensation. As a result, operating margin declined."
        ),
        "max_tokens": 128,
        "temperature": 0.2,
    },
    {
        "question": "What were the main business drivers of revenue growth?",
        "context": (
            "The company reported stronger enterprise demand, higher renewal rates, "
            "and increased adoption of premium products. These factors contributed "
            "to revenue growth during the quarter."
        ),
        "max_tokens": 128,
        "temperature": 0.2,
    },
    {
        "question": "What is the key risk mentioned in the update?",
        "context": (
            "Management noted that revenue growth remains healthy, but warned that "
            "foreign exchange pressure and rising infrastructure costs could affect "
            "profitability next quarter."
        ),
        "max_tokens": 128,
        "temperature": 0.2,
    },
    {
        "question": "How should investors interpret the cash flow trend?",
        "context": (
            "Operating cash flow improved year over year due to better collections "
            "and disciplined working capital management. Capital expenditures remained "
            "elevated because of infrastructure investments."
        ),
        "max_tokens": 128,
        "temperature": 0.2,
    },
]


def percentile(values, percent):
    if not values:
        return None

    values = sorted(values)
    index = int((percent / 100) * (len(values) - 1))
    return values[index]


def post_json(url, payload, timeout):
    data = json.dumps(payload).encode("utf-8")

    req = urllib_request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()

    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            elapsed = time.perf_counter() - start

            return {
                "ok": True,
                "status_code": response.status,
                "latency_seconds": elapsed,
                "response": json.loads(body),
                "error": None,
            }

    except HTTPError as exc:
        elapsed = time.perf_counter() - start
        error_body = exc.read().decode("utf-8", errors="replace")

        return {
            "ok": False,
            "status_code": exc.code,
            "latency_seconds": elapsed,
            "response": None,
            "error": error_body,
        }

    except URLError as exc:
        elapsed = time.perf_counter() - start

        return {
            "ok": False,
            "status_code": None,
            "latency_seconds": elapsed,
            "response": None,
            "error": str(exc),
        }


def run_load_test(base_url, num_requests, concurrency, timeout):
    url = f"{base_url.rstrip('/')}/qa"

    all_results = []
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []

        for i in range(num_requests):
            payload = QA_PAYLOADS[i % len(QA_PAYLOADS)]
            futures.append(executor.submit(post_json, url, payload, timeout))

        for future in as_completed(futures):
            all_results.append(future.result())

    total_time = time.perf_counter() - start

    successful = [r for r in all_results if r["ok"]]
    failed = [r for r in all_results if not r["ok"]]
    latencies = [r["latency_seconds"] for r in successful]

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    for result in successful:
        usage = result["response"].get("usage", {})
        total_prompt_tokens += int(usage.get("prompt_tokens", 0))
        total_completion_tokens += int(usage.get("completion_tokens", 0))
        total_tokens += int(usage.get("total_tokens", 0))

    report = {
        "endpoint": "/qa",
        "base_url": base_url,
        "num_requests": num_requests,
        "concurrency": concurrency,
        "total_time_seconds": total_time,
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "requests_per_second": len(successful) / total_time if total_time > 0 else 0,
        "latency_seconds": {
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
            "mean": statistics.mean(latencies) if latencies else None,
            "p50": statistics.median(latencies) if latencies else None,
            "p95": percentile(latencies, 95),
        },
        "tokens": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_tokens_per_second": total_tokens / total_time if total_time > 0 else 0,
            "completion_tokens_per_second": total_completion_tokens / total_time if total_time > 0 else 0,
        },
        "errors": failed[:5],
        "individual_results": all_results,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Load test the /qa endpoint.")

    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="FastAPI base URL",
    )

    parser.add_argument(
        "--num-requests",
        type=int,
        default=20,
        help="Total number of requests",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of concurrent requests",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Request timeout in seconds",
    )

    parser.add_argument(
        "--output",
        default="reports/load_test_qa_day17.json",
        help="Output JSON report",
    )

    args = parser.parse_args()

    report = run_load_test(
        base_url=args.base_url,
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print("QA Load Test Summary")
    print("=" * 80)
    print(f"Endpoint: {report['endpoint']}")
    print(f"Requests: {report['num_requests']}")
    print(f"Concurrency: {report['concurrency']}")
    print(f"Successful: {report['successful_requests']}")
    print(f"Failed: {report['failed_requests']}")
    print(f"Total time: {report['total_time_seconds']:.3f}s")
    print(f"Requests/sec: {report['requests_per_second']:.3f}")
    print(f"Mean latency: {report['latency_seconds']['mean']:.3f}s")
    print(f"P50 latency: {report['latency_seconds']['p50']:.3f}s")
    print(f"P95 latency: {report['latency_seconds']['p95']:.3f}s")
    print(f"Total tokens/sec: {report['tokens']['total_tokens_per_second']:.3f}")
    print(f"Completion tokens/sec: {report['tokens']['completion_tokens_per_second']:.3f}")
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()