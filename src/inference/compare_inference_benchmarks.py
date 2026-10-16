import argparse
import json
from pathlib import Path


def load_json(path: str) -> dict:
    report_path = Path(path)

    if not report_path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt(value) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def write_latency_table(f, latency_reports):
    f.write("## Latency Comparison\n\n")
    f.write(
        "| Run | Max Tokens | Requests | Mean Latency (s) | "
        "P50 Latency (s) | P95 Latency (s) | Min (s) | Max (s) |\n"
    )
    f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")

    for name, path in latency_reports:
        report = load_json(path)
        latency = report["latency_seconds"]

        f.write(
            f"| {name} "
            f"| {report.get('max_tokens', '')} "
            f"| {report.get('num_requests', '')} "
            f"| {fmt(latency.get('mean'))} "
            f"| {fmt(latency.get('median_p50'))} "
            f"| {fmt(latency.get('p95'))} "
            f"| {fmt(latency.get('min'))} "
            f"| {fmt(latency.get('max'))} |\n"
        )

    f.write("\n")


def write_throughput_table(f, throughput_reports):
    f.write("## Throughput Comparison\n\n")
    f.write(
        "| Run | Concurrency | Requests | Total Time (s) | Requests/sec | "
        "Total Tokens/sec | Completion Tokens/sec |\n"
    )
    f.write("|---|---:|---:|---:|---:|---:|---:|\n")

    for name, path in throughput_reports:
        report = load_json(path)

        f.write(
            f"| {name} "
            f"| {report.get('concurrency', '')} "
            f"| {report.get('num_requests', '')} "
            f"| {fmt(report.get('total_time_seconds'))} "
            f"| {fmt(report.get('requests_per_second'))} "
            f"| {fmt(report.get('total_tokens_per_second'))} "
            f"| {fmt(report.get('completion_tokens_per_second'))} |\n"
        )

    f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compare vLLM inference benchmark reports."
    )

    parser.add_argument(
        "--latency-reports",
        nargs="*",
        default=[],
        help="Latency reports in name=path format",
    )

    parser.add_argument(
        "--throughput-reports",
        nargs="*",
        default=[],
        help="Throughput reports in name=path format",
    )

    parser.add_argument(
        "--output",
        default="reports/inference_benchmark_comparison_day13.md",
        help="Output markdown report",
    )

    args = parser.parse_args()

    latency_reports = []
    for item in args.latency_reports:
        name, path = item.split("=", 1)
        latency_reports.append((name, path))

    throughput_reports = []
    for item in args.throughput_reports:
        name, path = item.split("=", 1)
        throughput_reports.append((name, path))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Day 13 Inference Benchmark Comparison\n\n")

        f.write("## Goal\n\n")
        f.write(
            "The goal of Day 13 was to compare vLLM serving performance "
            "under different generation lengths and concurrency levels.\n\n"
        )

        f.write("## Serving Setup\n\n")
        f.write("| Item | Value |\n")
        f.write("|---|---|\n")
        f.write("| Serving engine | vLLM |\n")
        f.write("| API format | OpenAI-compatible API |\n")
        f.write("| Served model | `finance-qwen1.5b` |\n")
        f.write("| Base model | `Qwen/Qwen2.5-1.5B-Instruct` |\n")
        f.write("| Endpoint | `http://localhost:8001/v1/chat/completions` |\n")
        f.write("| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |\n")
        f.write("| VRAM | ~8GB |\n\n")

        if latency_reports:
            write_latency_table(f, latency_reports)

        if throughput_reports:
            write_throughput_table(f, throughput_reports)

        f.write("## Interpretation\n\n")
        f.write(
            "The latency benchmark shows how response time changes as the "
            "maximum generation length increases. Higher `max_tokens` usually "
            "increases latency because the model may generate more tokens.\n\n"
        )

        f.write(
            "The throughput benchmark shows how vLLM handles concurrent requests. "
            "Increasing concurrency can improve overall requests/sec and tokens/sec, "
            "but it may also increase individual request latency if the GPU becomes saturated.\n\n"
        )

        f.write(
            "These results create a serving baseline for the finance AI platform "
            "and will be used later when comparing different serving backends, "
            "quantization settings, or model sizes.\n"
        )

    print(f"Day 13 comparison report saved to: {output_path}")


if __name__ == "__main__":
    main()