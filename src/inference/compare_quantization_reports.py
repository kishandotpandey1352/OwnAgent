import argparse
import json
from pathlib import Path


def load_report(path: str):
    report_path = Path(path)

    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt(value):
    if value is None:
        return "N/A"

    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def extract_row(name: str, path: str):
    report = load_report(path)

    memory = report.get("memory", {})
    latency = report.get("latency_seconds", {})
    tokens = report.get("tokens", {})

    return {
        "name": name,
        "path": path,
        "model_name": report.get("model_name"),
        "quantization": report.get("quantization"),
        "num_requests": report.get("num_requests"),
        "max_new_tokens": report.get("max_new_tokens"),
        "load_time_seconds": report.get("load_time_seconds"),
        "mean_latency": latency.get("mean"),
        "p50_latency": latency.get("p50"),
        "p95_latency": latency.get("p95"),
        "mean_completion_tps": tokens.get("mean_completion_tokens_per_second"),
        "allocated_gb": memory.get("allocated_gb"),
        "reserved_gb": memory.get("reserved_gb"),
        "max_allocated_gb": memory.get("max_allocated_gb"),
        "max_reserved_gb": memory.get("max_reserved_gb"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare quantization benchmark reports."
    )

    parser.add_argument(
        "--reports",
        nargs="+",
        required=True,
        help="Reports in name=path format",
    )

    parser.add_argument(
        "--output",
        default="reports/quantization_comparison_day14.md",
        help="Output markdown path",
    )

    args = parser.parse_args()

    rows = []

    for item in args.reports:
        name, path = item.split("=", 1)
        rows.append(extract_row(name=name, path=path))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Day 14 Quantization Comparison\n\n")

        f.write("## Goal\n\n")
        f.write(
            "The goal of Day 14 was to compare INT8 and INT4 quantized inference "
            "for the finance model serving pipeline.\n\n"
        )

        f.write("## Setup\n\n")
        f.write("| Item | Value |\n")
        f.write("|---|---|\n")
        f.write("| Model | `Qwen/Qwen2.5-3B-Instruct` |\n")
        f.write("| Runtime | Transformers + bitsandbytes |\n")
        f.write("| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |\n")
        f.write("| VRAM | ~8GB |\n")
        f.write("| Task | Financial summarization prompt |\n\n")

        f.write("## Results\n\n")
        f.write(
            "| Run | Quantization | Requests | Max New Tokens | Load Time (s) | "
            "Mean Latency (s) | P50 (s) | P95 (s) | Completion Tokens/sec | "
            "Max Allocated VRAM (GB) | Max Reserved VRAM (GB) |\n"
        )
        f.write("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")

        for row in rows:
            f.write(
                f"| {row['name']} "
                f"| {row['quantization']} "
                f"| {row['num_requests']} "
                f"| {row['max_new_tokens']} "
                f"| {fmt(row['load_time_seconds'])} "
                f"| {fmt(row['mean_latency'])} "
                f"| {fmt(row['p50_latency'])} "
                f"| {fmt(row['p95_latency'])} "
                f"| {fmt(row['mean_completion_tps'])} "
                f"| {fmt(row['max_allocated_gb'])} "
                f"| {fmt(row['max_reserved_gb'])} |\n"
            )

        f.write("\n## Interpretation\n\n")
        f.write(
            "INT8 quantization reduces model memory compared with FP16 while usually "
            "preserving more numerical precision than INT4. INT4 quantization reduces "
            "memory further, which can make larger models practical on limited VRAM, "
            "but it may affect output quality or latency depending on kernels and hardware.\n\n"
        )

        f.write(
            "For this local setup, the key question is whether INT8 or INT4 allows "
            "Qwen2.5-3B-Instruct to run comfortably on the RTX 5060 Laptop GPU while "
            "maintaining acceptable latency and output quality.\n\n"
        )

        f.write("## Notes\n\n")
        f.write(
            "Day 14 uses Transformers + bitsandbytes for quantization benchmarking. "
            "vLLM serving remains available for the smaller `finance-qwen1.5b` model, "
            "while quantization experiments are used to understand memory tradeoffs "
            "for the larger Qwen2.5-3B model.\n"
        )

    print(f"Quantization comparison report saved to: {output_path}")


if __name__ == "__main__":
    main()