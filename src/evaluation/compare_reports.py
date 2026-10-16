import argparse
import json
from pathlib import Path


METRIC_KEYS = [
    "rouge1",
    "rouge2",
    "rougeL",
    "rougeLsum",
    "bertscore_precision",
    "bertscore_recall",
    "bertscore_f1",
    "empty_predictions",
    "empty_references",
]


def load_report(path: str) -> dict:
    report_path = Path(path)

    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        report = json.load(f)

    if "metrics" not in report:
        raise ValueError(f"Report does not contain a 'metrics' section: {report_path}")

    return report


def safe_metric(metrics: dict, key: str, default=0.0):
    value = metrics.get(key, default)

    if value is None:
        return default

    return value


def format_float(value) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def extract_row(name: str, report_path: str) -> dict:
    report = load_report(report_path)
    metrics = report["metrics"]

    row = {
        "name": name,
        "report_path": report_path,
    }

    for key in METRIC_KEYS:
        row[key] = safe_metric(metrics, key)

    return row


def choose_best_run(rows: list[dict]) -> dict:
    """
    Select the best run by BERTScore F1 first, then ROUGE-L as tie-breaker.
    """
    return max(
        rows,
        key=lambda row: (
            float(row.get("bertscore_f1", 0.0)),
            float(row.get("rougeL", 0.0)),
        ),
    )


def write_markdown_report(rows: list[dict], output_path: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    best = choose_best_run(rows)

    with output.open("w", encoding="utf-8") as f:
        f.write("# Day 9 Evaluation Summary\n\n")

        f.write("## Experiment Setup\n\n")
        f.write("Base model: `Qwen/Qwen2.5-3B-Instruct`  \n")
        f.write("Fine-tuning method: QLoRA  \n")
        f.write("Dataset: Finance gold dataset  \n")
        f.write("Train examples: 240  \n")
        f.write("Test examples: 60  \n")
        f.write("Evaluation set: `data/instruction/finance_gold_test.jsonl`  \n\n")

        f.write("## Compared Runs\n\n")
        f.write("| Run | Report File |\n")
        f.write("|---|---|\n")

        for row in rows:
            f.write(f"| {row['name']} | `{row['report_path']}` |\n")

        f.write("\n## Metrics\n\n")
        f.write(
            "| Model / Run | ROUGE-1 | ROUGE-2 | ROUGE-L | ROUGE-Lsum | "
            "BERTScore Precision | BERTScore Recall | BERTScore F1 | "
            "Empty Predictions | Empty References |\n"
        )
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")

        for row in rows:
            f.write(
                f"| {row['name']} "
                f"| {format_float(row['rouge1'])} "
                f"| {format_float(row['rouge2'])} "
                f"| {format_float(row['rougeL'])} "
                f"| {format_float(row['rougeLsum'])} "
                f"| {format_float(row['bertscore_precision'])} "
                f"| {format_float(row['bertscore_recall'])} "
                f"| {format_float(row['bertscore_f1'])} "
                f"| {int(row['empty_predictions'])} "
                f"| {int(row['empty_references'])} |\n"
            )

        f.write("\n## Best Run\n\n")
        f.write(f"Best run by BERTScore F1: **{best['name']}**  \n")
        f.write(f"BERTScore F1: **{format_float(best['bertscore_f1'])}**  \n")
        f.write(f"ROUGE-L: **{format_float(best['rougeL'])}**  \n\n")

        f.write("## Interpretation\n\n")
        f.write(
            "This report compares the base model against multiple QLoRA adapters "
            "trained with different hyperparameter settings. All models are evaluated "
            "on the same held-out finance test set, so the comparison is fair as long "
            "as all JSON reports were generated using the same evaluation script.\n\n"
        )

        f.write(
            "The selected best run is based primarily on BERTScore F1, with ROUGE-L "
            "used as a secondary signal. Empty prediction counts are included because "
            "a model that produces blank or invalid outputs should not be selected even "
            "if some metrics appear competitive.\n"
        )

    print(f"Comparison report saved to: {output}")


def write_json_summary(rows: list[dict], markdown_output_path: str) -> None:
    markdown_path = Path(markdown_output_path)
    json_path = markdown_path.with_suffix(".json")

    best = choose_best_run(rows)

    summary = {
        "best_run": best["name"],
        "best_run_report": best["report_path"],
        "selection_metric": "bertscore_f1",
        "tie_breaker_metric": "rougeL",
        "runs": rows,
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"JSON summary saved to: {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare evaluation report JSON files and create a markdown summary."
    )

    parser.add_argument(
        "--reports",
        nargs="+",
        required=True,
        help="List of evaluation report JSON files",
    )

    parser.add_argument(
        "--names",
        nargs="+",
        required=True,
        help="Names for each report",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="reports/evaluation_summary_day9.md",
        help="Output markdown summary path",
    )

    args = parser.parse_args()

    if len(args.reports) != len(args.names):
        raise ValueError(
            "The number of --reports must match the number of --names."
        )

    rows = [
        extract_row(name=name, report_path=report_path)
        for name, report_path in zip(args.names, args.reports)
    ]

    write_markdown_report(rows=rows, output_path=args.output)
    write_json_summary(rows=rows, markdown_output_path=args.output)


if __name__ == "__main__":
    main()