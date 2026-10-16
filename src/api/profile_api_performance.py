import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


ENDPOINT_PAYLOADS = {
    "/summarize": {
        "text": (
            "Revenue increased by 18 percent due to stronger enterprise demand. "
            "However, operating expenses also rose because of higher cloud infrastructure "
            "costs and employee compensation. Management expects margin pressure to continue."
        ),
        "max_tokens": 128,
        "temperature": 0.2,
    },
    "/qa": {
        "question": "Why did operating margin decline?",
        "context": (
            "Revenue increased by 18 percent due to stronger enterprise demand. "
            "However, operating expenses increased because of higher cloud infrastructure "
            "costs and employee compensation. As a result, operating margin declined."
        ),
        "max_tokens": 128,
        "temperature": 0.2,
    },
    "/risk-analysis": {
        "text": (
            "Revenue increased by 18 percent due to stronger enterprise demand. "
            "However, gross margin declined because of higher cloud infrastructure costs. "
            "Operating expenses increased due to hiring and employee compensation. "
            "Management warned that margin pressure may continue next quarter."
        ),
        "max_tokens": 192,
        "temperature": 0.2,
    },
}


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


def extract_usage(result):
    if not result["ok"] or not result["response"]:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    usage = result["response"].get("usage", {})

    return {
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "total_tokens": int(usage.get("total_tokens", 0)),
    }


def summarize_results(endpoint, results, total_time):
    successful = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    latencies = [r["latency_seconds"] for r in successful]

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    for result in successful:
        usage = extract_usage(result)
        total_prompt_tokens += usage["prompt_tokens"]
        total_completion_tokens += usage["completion_tokens"]
        total_tokens += usage["total_tokens"]

    return {
        "endpoint": endpoint,
        "total_time_seconds": total_time,
        "requests": len(results),
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
        "sample_errors": failed[:3],
    }


def profile_endpoint(base_url, endpoint, num_requests, concurrency, timeout):
    url = f"{base_url.rstrip('/')}{endpoint}"
    payload = ENDPOINT_PAYLOADS[endpoint]

    results = []
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(post_json, url, payload, timeout)
            for _ in range(num_requests)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    total_time = time.perf_counter() - start

    return summarize_results(endpoint, results, total_time)


def write_markdown_report(report, output_md):
    output_path = Path(output_md)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Day 18 API Performance Profiling Report\n\n")

        f.write("## Goal\n\n")
        f.write(
            "The goal of Day 18 was to add the `/risk-analysis` endpoint and profile "
            "the performance of all three finance API endpoints.\n\n"
        )

        f.write("## Profiling Setup\n\n")
        f.write("| Item | Value |\n")
        f.write("|---|---|\n")
        f.write(f"| Base URL | `{report['base_url']}` |\n")
        f.write(f"| Requests per endpoint | {report['num_requests']} |\n")
        f.write(f"| Concurrency | {report['concurrency']} |\n")
        f.write("| Backend | FastAPI connected to vLLM |\n")
        f.write("| Served model | `finance-qwen1.5b` |\n\n")

        f.write("## Endpoint Performance\n\n")
        f.write(
            "| Endpoint | Successful | Failed | Requests/sec | Mean Latency (s) | "
            "P50 (s) | P95 (s) | Total Tokens/sec | Completion Tokens/sec |\n"
        )
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")

        for endpoint_report in report["endpoints"]:
            latency = endpoint_report["latency_seconds"]
            tokens = endpoint_report["tokens"]

            f.write(
                f"| {endpoint_report['endpoint']} "
                f"| {endpoint_report['successful_requests']} "
                f"| {endpoint_report['failed_requests']} "
                f"| {endpoint_report['requests_per_second']:.3f} "
                f"| {latency['mean']:.3f} "
                f"| {latency['p50']:.3f} "
                f"| {latency['p95']:.3f} "
                f"| {tokens['total_tokens_per_second']:.3f} "
                f"| {tokens['completion_tokens_per_second']:.3f} |\n"
            )

        f.write("\n## Interpretation\n\n")
        f.write(
            "The profiling results compare the behavior of the summarization, "
            "financial QA, and risk-analysis endpoints under the same request count "
            "and concurrency level. Differences in latency are expected because each "
            "endpoint uses a different prompt structure and may generate different "
            "numbers of tokens.\n\n"
        )

        f.write(
            "The `/risk-analysis` endpoint usually has a longer structured prompt and "
            "may generate a longer response, so it can have higher latency than shorter "
            "summarization or QA requests.\n\n"
        )

        f.write("## Day 18 Status\n\n")
        f.write(
            "Day 18 is complete when the `/risk-analysis` endpoint returns structured "
            "risk analysis and the profiling report is generated successfully.\n"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Profile FastAPI finance endpoints."
    )

    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="FastAPI base URL",
    )

    parser.add_argument(
        "--num-requests",
        type=int,
        default=10,
        help="Requests per endpoint",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Concurrent requests per endpoint",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Request timeout in seconds",
    )

    parser.add_argument(
        "--output-json",
        default="reports/api_performance_profile_day18.json",
        help="Output JSON report",
    )

    parser.add_argument(
        "--output-md",
        default="reports/api_performance_profile_day18.md",
        help="Output Markdown report",
    )

    args = parser.parse_args()

    endpoint_reports = []

    for endpoint in ["/summarize", "/qa", "/risk-analysis"]:
        print(f"Profiling {endpoint} ...")
        endpoint_report = profile_endpoint(
            base_url=args.base_url,
            endpoint=endpoint,
            num_requests=args.num_requests,
            concurrency=args.concurrency,
            timeout=args.timeout,
        )
        endpoint_reports.append(endpoint_report)

    report = {
        "base_url": args.base_url,
        "num_requests": args.num_requests,
        "concurrency": args.concurrency,
        "endpoints": endpoint_reports,
    }

    output_json_path = Path(args.output_json)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    write_markdown_report(report, args.output_md)

    print("=" * 80)
    print("Day 18 Performance Profile Summary")
    print("=" * 80)

    for endpoint_report in endpoint_reports:
        latency = endpoint_report["latency_seconds"]
        tokens = endpoint_report["tokens"]

        print(f"Endpoint: {endpoint_report['endpoint']}")
        print(f"  Successful: {endpoint_report['successful_requests']}")
        print(f"  Failed: {endpoint_report['failed_requests']}")
        print(f"  Requests/sec: {endpoint_report['requests_per_second']:.3f}")
        print(f"  Mean latency: {latency['mean']:.3f}s")
        print(f"  P95 latency: {latency['p95']:.3f}s")
        print(f"  Total tokens/sec: {tokens['total_tokens_per_second']:.3f}")
        print()

    print(f"JSON report saved to: {output_json_path}")
    print(f"Markdown report saved to: {args.output_md}")


if __name__ == "__main__":
    main()