import argparse
import json
from pathlib import Path


def load_json(path: str):
    report_path = Path(path)

    if not report_path.exists():
        raise FileNotFoundError(f"File not found: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt(value, digits=3):
    if value is None:
        return "N/A"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def write_serving_setup(f):
    f.write("# Inference Benchmark Report\n\n")

    f.write("## 1. Goal\n\n")
    f.write(
        "The goal of this report is to summarize inference performance for the "
        "finance AI platform. The benchmark focuses on latency, throughput, "
        "quantization, and GPU memory tradeoffs.\n\n"
    )

    f.write("## 2. Serving Setup\n\n")
    f.write("| Item | Value |\n")
    f.write("|---|---|\n")
    f.write("| Local serving engine | vLLM |\n")
    f.write("| vLLM served model | `finance-qwen1.5b` |\n")
    f.write("| vLLM base model | `Qwen/Qwen2.5-1.5B-Instruct` |\n")
    f.write("| Quantization benchmark model | `Qwen/Qwen2.5-3B-Instruct` |\n")
    f.write("| Quantization runtime | Transformers + bitsandbytes |\n")
    f.write("| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |\n")
    f.write("| VRAM | ~8GB |\n")
    f.write("| API format | OpenAI-compatible API |\n\n")


def write_batch_vs_throughput(f, throughput_reports):
    f.write("## 3. Batch Size / Concurrency vs Throughput\n\n")
    f.write(
        "In this local vLLM benchmark, concurrency is used as the practical "
        "serving equivalent of batch pressure. Higher concurrency means multiple "
        "requests are sent to the server at the same time.\n\n"
    )

    f.write("| Run | Concurrency | Requests | Max Tokens | Total Time (s) | Requests/sec | Total Tokens/sec | Completion Tokens/sec |\n")
    f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")

    for name, path in throughput_reports:
        report = load_json(path)

        f.write(
            f"| {name} "
            f"| {report.get('concurrency', 'N/A')} "
            f"| {report.get('num_requests', 'N/A')} "
            f"| {report.get('max_tokens', 'N/A')} "
            f"| {fmt(report.get('total_time_seconds'))} "
            f"| {fmt(report.get('requests_per_second'))} "
            f"| {fmt(report.get('total_tokens_per_second'))} "
            f"| {fmt(report.get('completion_tokens_per_second'))} |\n"
        )

    f.write("\n")


def write_latency_by_generation_length(f, latency_reports):
    f.write("## 4. Generation Length vs Latency\n\n")
    f.write(
        "This table shows how latency changes as the maximum generation length "
        "increases. Longer generations usually increase latency because the model "
        "must decode more tokens.\n\n"
    )

    f.write("| Run | Max Tokens | Requests | Mean Latency (s) | P50 Latency (s) | P95 Latency (s) | Min (s) | Max (s) |\n")
    f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")

    for name, path in latency_reports:
        report = load_json(path)
        latency = report.get("latency_seconds", {})

        f.write(
            f"| {name} "
            f"| {report.get('max_tokens', 'N/A')} "
            f"| {report.get('num_requests', 'N/A')} "
            f"| {fmt(latency.get('mean'))} "
            f"| {fmt(latency.get('median_p50'))} "
            f"| {fmt(latency.get('p95'))} "
            f"| {fmt(latency.get('min'))} "
            f"| {fmt(latency.get('max'))} |\n"
        )

    f.write("\n")


def write_int4_vs_fp16(f, quant_reports):
    f.write("## 5. INT4 vs FP16 Quantization\n\n")
    f.write(
        "This table compares different model loading modes for "
        "`Qwen/Qwen2.5-3B-Instruct` using Transformers and bitsandbytes. "
        "The purpose is to understand the tradeoff between speed and memory usage.\n\n"
    )

    f.write("| Run | Quantization | Requests | Max New Tokens | Load Time (s) | Mean Latency (s) | P50 (s) | P95 (s) | Completion Tokens/sec | Max Allocated VRAM (GB) | Max Reserved VRAM (GB) |\n")
    f.write("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")

    for name, path in quant_reports:
        report = load_json(path)
        latency = report.get("latency_seconds", {})
        tokens = report.get("tokens", {})
        memory = report.get("memory", {})

        f.write(
            f"| {name} "
            f"| {report.get('quantization', 'N/A')} "
            f"| {report.get('num_requests', 'N/A')} "
            f"| {report.get('max_new_tokens', 'N/A')} "
            f"| {fmt(report.get('load_time_seconds'))} "
            f"| {fmt(latency.get('mean'))} "
            f"| {fmt(latency.get('p50'))} "
            f"| {fmt(latency.get('p95'))} "
            f"| {fmt(tokens.get('mean_completion_tokens_per_second'))} "
            f"| {fmt(memory.get('max_allocated_gb'))} "
            f"| {fmt(memory.get('max_reserved_gb'))} |\n"
        )

    f.write("\n")


def write_memory_vs_latency(f, quant_reports):
    f.write("## 6. Memory vs Latency\n\n")
    f.write(
        "This table focuses specifically on the relationship between GPU memory "
        "usage and response latency. Lower memory usage is useful for limited VRAM, "
        "but it does not always mean faster inference.\n\n"
    )

    f.write("| Run | Quantization | Max Allocated VRAM (GB) | Mean Latency (s) | Completion Tokens/sec |\n")
    f.write("|---|---|---:|---:|---:|\n")

    for name, path in quant_reports:
        report = load_json(path)
        latency = report.get("latency_seconds", {})
        tokens = report.get("tokens", {})
        memory = report.get("memory", {})

        f.write(
            f"| {name} "
            f"| {report.get('quantization', 'N/A')} "
            f"| {fmt(memory.get('max_allocated_gb'))} "
            f"| {fmt(latency.get('mean'))} "
            f"| {fmt(tokens.get('mean_completion_tokens_per_second'))} |\n"
        )

    f.write("\n")


def write_interpretation(f):
    f.write("## 7. Interpretation\n\n")

    f.write("### Batch Size / Concurrency vs Throughput\n\n")
    f.write(
        "Increasing concurrency can improve throughput because vLLM can process "
        "multiple requests together. However, if concurrency becomes too high for "
        "the local GPU, individual latency may increase or throughput may stop improving.\n\n"
    )

    f.write("### INT4 vs FP16\n\n")
    f.write(
        "FP16 usually provides the fastest inference when the model fits comfortably "
        "in GPU memory. INT4 uses much less VRAM, which makes it useful for running "
        "larger models on limited hardware. In this project, INT4 allowed "
        "Qwen2.5-3B-Instruct to run with much lower memory usage than FP16.\n\n"
    )

    f.write("### Memory vs Latency\n\n")
    f.write(
        "Lower memory usage does not always mean lower latency. Quantized inference "
        "can be slower or faster depending on kernel support, GPU architecture, and "
        "runtime implementation. The practical choice depends on whether the priority "
        "is speed, memory efficiency, or serving stability.\n\n"
    )

    f.write("## 8. Final Conclusion\n\n")
    f.write(
        "The inference benchmarks show that the local platform can serve models through "
        "vLLM and can also run the larger Qwen2.5-3B-Instruct model using quantized "
        "Transformers inference. For reliable local vLLM serving, `finance-qwen1.5b` "
        "is the practical model. For memory-efficient local inference with the larger "
        "3B model, INT4 is the most practical option.\n"
    )


def parse_named_paths(items):
    parsed = []

    for item in items:
        if "=" not in item:
            raise ValueError(
                f"Invalid report format: {item}. Expected name=path"
            )

        name, path = item.split("=", 1)
        parsed.append((name, path))

    return parsed


def main():
    parser = argparse.ArgumentParser(
        description="Create final inference benchmark report."
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
        "--quantization-reports",
        nargs="*",
        default=[],
        help="Quantization reports in name=path format",
    )

    parser.add_argument(
        "--output",
        default="reports/inference_benchmark_report.md",
        help="Output markdown report",
    )

    args = parser.parse_args()

    latency_reports = parse_named_paths(args.latency_reports)
    throughput_reports = parse_named_paths(args.throughput_reports)
    quant_reports = parse_named_paths(args.quantization_reports)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        write_serving_setup(f)

        if throughput_reports:
            write_batch_vs_throughput(f, throughput_reports)

        if latency_reports:
            write_latency_by_generation_length(f, latency_reports)

        if quant_reports:
            write_int4_vs_fp16(f, quant_reports)
            write_memory_vs_latency(f, quant_reports)

        write_interpretation(f)

    print(f"Inference benchmark report saved to: {output_path}")


if __name__ == "__main__":
    main()