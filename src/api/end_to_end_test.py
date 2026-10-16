import argparse
import json
import time
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


TEST_CASES = [
    {
        "name": "summarize",
        "endpoint": "/summarize",
        "payload": {
            "text": (
                "Revenue increased by 18 percent due to stronger enterprise demand. "
                "However, operating expenses also rose because of higher cloud infrastructure "
                "costs and employee compensation. Management expects margin pressure to continue."
            ),
            "max_tokens": 128,
            "temperature": 0.2,
        },
        "expected_field": "summary",
    },
    {
        "name": "qa",
        "endpoint": "/qa",
        "payload": {
            "question": "Why did operating margin decline?",
            "context": (
                "Revenue increased by 18 percent due to stronger enterprise demand. "
                "However, operating expenses increased because of higher cloud infrastructure "
                "costs and employee compensation. As a result, operating margin declined."
            ),
            "max_tokens": 128,
            "temperature": 0.2,
        },
        "expected_field": "answer",
    },
    {
        "name": "risk_analysis",
        "endpoint": "/risk-analysis",
        "payload": {
            "text": (
                "Revenue increased by 18 percent due to stronger enterprise demand. "
                "However, gross margin declined because of higher cloud infrastructure costs. "
                "Operating expenses also increased due to hiring and employee compensation. "
                "Management warned that margin pressure may continue next quarter."
            ),
            "max_tokens": 192,
            "temperature": 0.2,
        },
        "expected_field": "risk_analysis",
    },
]


def get_url(url, timeout):
    start = time.perf_counter()

    try:
        with urllib_request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            elapsed = time.perf_counter() - start

            return {
                "ok": 200 <= response.status < 300,
                "status_code": response.status,
                "latency_seconds": elapsed,
                "body": body,
                "error": None,
            }

    except (HTTPError, URLError) as exc:
        elapsed = time.perf_counter() - start

        return {
            "ok": False,
            "status_code": getattr(exc, "code", None),
            "latency_seconds": elapsed,
            "body": None,
            "error": str(exc),
        }


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
            body = response.read().decode("utf-8", errors="replace")
            elapsed = time.perf_counter() - start
            parsed = json.loads(body)

            return {
                "ok": 200 <= response.status < 300,
                "status_code": response.status,
                "latency_seconds": elapsed,
                "response": parsed,
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

    except (URLError, json.JSONDecodeError) as exc:
        elapsed = time.perf_counter() - start

        return {
            "ok": False,
            "status_code": None,
            "latency_seconds": elapsed,
            "response": None,
            "error": str(exc),
        }


def validate_api_response(result, expected_field):
    if not result["ok"]:
        return False, "request_failed"

    response = result.get("response") or {}

    if expected_field not in response:
        return False, f"missing_field:{expected_field}"

    if not str(response.get(expected_field, "")).strip():
        return False, f"empty_field:{expected_field}"

    usage = response.get("usage", {})

    if int(usage.get("total_tokens", 0)) <= 0:
        return False, "missing_or_zero_tokens"

    return True, "passed"


def main():
    parser = argparse.ArgumentParser(
        description="Run end-to-end tests for the Finance AI Platform."
    )

    parser.add_argument(
        "--api-base-url",
        default="http://localhost:8000",
        help="FastAPI base URL",
    )

    parser.add_argument(
        "--vllm-base-url",
        default="http://localhost:8001",
        help="vLLM base URL",
    )

    parser.add_argument(
        "--prometheus-url",
        default="http://localhost:9090",
        help="Prometheus base URL",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Request timeout in seconds",
    )

    parser.add_argument(
        "--output-json",
        default="reports/end_to_end_day20.json",
        help="Output JSON path",
    )

    parser.add_argument(
        "--output-md",
        default="reports/end_to_end_day20.md",
        help="Output Markdown path",
    )

    args = parser.parse_args()

    checks = []

    health = get_url(f"{args.api_base_url.rstrip('/')}/health", args.timeout)
    checks.append(
        {
            "name": "fastapi_health",
            "ok": health["ok"],
            "status_code": health["status_code"],
            "latency_seconds": health["latency_seconds"],
            "error": health["error"],
        }
    )

    metrics = get_url(f"{args.api_base_url.rstrip('/')}/metrics", args.timeout)
    metrics_ok = metrics["ok"] and metrics["body"] and "finance_api_requests_total" in metrics["body"]
    checks.append(
        {
            "name": "fastapi_metrics",
            "ok": bool(metrics_ok),
            "status_code": metrics["status_code"],
            "latency_seconds": metrics["latency_seconds"],
            "error": metrics["error"],
        }
    )

    vllm_models = get_url(f"{args.vllm_base_url.rstrip('/')}/v1/models", args.timeout)
    vllm_ok = vllm_models["ok"] and vllm_models["body"] and "finance-qwen1.5b" in vllm_models["body"]
    checks.append(
        {
            "name": "vllm_models",
            "ok": bool(vllm_ok),
            "status_code": vllm_models["status_code"],
            "latency_seconds": vllm_models["latency_seconds"],
            "error": vllm_models["error"],
        }
    )

    prometheus = get_url(f"{args.prometheus_url.rstrip('/')}/-/ready", args.timeout)
    checks.append(
        {
            "name": "prometheus_ready",
            "ok": prometheus["ok"],
            "status_code": prometheus["status_code"],
            "latency_seconds": prometheus["latency_seconds"],
            "error": prometheus["error"],
        }
    )

    endpoint_results = []

    for test_case in TEST_CASES:
        result = post_json(
            url=f"{args.api_base_url.rstrip('/')}{test_case['endpoint']}",
            payload=test_case["payload"],
            timeout=args.timeout,
        )

        passed, validation_message = validate_api_response(
            result,
            test_case["expected_field"],
        )

        response = result.get("response") or {}
        usage = response.get("usage", {})

        endpoint_results.append(
            {
                "name": test_case["name"],
                "endpoint": test_case["endpoint"],
                "ok": passed,
                "status_code": result["status_code"],
                "latency_seconds": result["latency_seconds"],
                "validation_message": validation_message,
                "model": response.get("model"),
                "usage": usage,
                "output_preview": str(response.get(test_case["expected_field"], ""))[:300],
                "error": result["error"],
            }
        )

    all_checks = checks + endpoint_results
    overall_status = "passed" if all(item["ok"] for item in all_checks) else "failed"

    report = {
        "overall_status": overall_status,
        "api_base_url": args.api_base_url,
        "vllm_base_url": args.vllm_base_url,
        "prometheus_url": args.prometheus_url,
        "service_checks": checks,
        "endpoint_tests": endpoint_results,
    }

    output_json_path = Path(args.output_json)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    output_md_path = Path(args.output_md)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)

    with output_md_path.open("w", encoding="utf-8") as f:
        f.write("# Day 20 End-to-End Test Report\n\n")

        f.write("## Goal\n\n")
        f.write(
            "The goal of Day 20 was to validate the complete local production-style "
            "Finance AI Platform from API request to model response and monitoring.\n\n"
        )

        f.write("## Overall Status\n\n")
        f.write(f"```text\n{overall_status.upper()}\n```\n\n")

        f.write("## Service Checks\n\n")
        f.write("| Check | Status | HTTP Status | Latency (s) |\n")
        f.write("|---|---|---:|---:|\n")

        for check in checks:
            status = "PASS" if check["ok"] else "FAIL"
            f.write(
                f"| {check['name']} "
                f"| {status} "
                f"| {check['status_code']} "
                f"| {check['latency_seconds']:.3f} |\n"
            )

        f.write("\n## Endpoint Tests\n\n")
        f.write("| Endpoint | Status | HTTP Status | Latency (s) | Model | Total Tokens |\n")
        f.write("|---|---|---:|---:|---|---:|\n")

        for result in endpoint_results:
            status = "PASS" if result["ok"] else "FAIL"
            usage = result.get("usage", {})
            f.write(
                f"| {result['endpoint']} "
                f"| {status} "
                f"| {result['status_code']} "
                f"| {result['latency_seconds']:.3f} "
                f"| {result.get('model')} "
                f"| {usage.get('total_tokens', 0)} |\n"
            )

        f.write("\n## Endpoint Output Previews\n\n")

        for result in endpoint_results:
            f.write(f"### {result['endpoint']}\n\n")
            f.write("```text\n")
            f.write(str(result.get("output_preview", "")))
            f.write("\n```\n\n")

        f.write("## Validated Architecture\n\n")
        f.write("```text\n")
        f.write("User / API Client\n")
        f.write("  ↓\n")
        f.write("FastAPI service\n")
        f.write("  ↓\n")
        f.write("vLLM backend\n")
        f.write("  ↓\n")
        f.write("finance-qwen1.5b\n")
        f.write("  ↓\n")
        f.write("Prometheus metrics\n")
        f.write("  ↓\n")
        f.write("Grafana dashboard\n")
        f.write("```\n\n")

        f.write("## Conclusion\n\n")

        if overall_status == "passed":
            f.write(
                "The end-to-end test passed. The Finance AI Platform successfully "
                "handled summarization, financial QA, and risk-analysis requests through "
                "FastAPI, routed them to the vLLM backend, returned model responses, and "
                "exposed monitoring metrics for Prometheus/Grafana.\n"
            )
        else:
            f.write(
                "The end-to-end test found one or more failing checks. Review the JSON "
                "report for details and fix the failing services or endpoints before "
                "marking Day 20 complete.\n"
            )

    print("=" * 80)
    print("Day 20 End-to-End Test")
    print("=" * 80)
    print(f"Overall status: {overall_status.upper()}")

    for item in all_checks:
        status = "PASS" if item["ok"] else "FAIL"
        print(f"{status} - {item['name']}")

    print(f"JSON report saved to: {output_json_path}")
    print(f"Markdown report saved to: {output_md_path}")


if __name__ == "__main__":
    main()