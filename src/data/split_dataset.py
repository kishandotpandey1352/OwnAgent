import argparse
import json
import random
from pathlib import Path
from collections import Counter


def read_jsonl(path: Path):
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}: {exc}") from exc

            rows.append(row)

    return rows


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def get_task(row):
    return row.get("metadata", {}).get("task", "unknown")


def stratified_split(rows, test_size: float, seed: int):
    """
    Keeps task distribution balanced across train/test.
    Example:
    100 summarization, 100 risk_analysis, 100 financial_qa
    becomes roughly:
    train = 80 each
    test = 20 each
    """
    random.seed(seed)

    grouped = {}

    for row in rows:
        task = get_task(row)
        grouped.setdefault(task, []).append(row)

    train_rows = []
    test_rows = []

    for task, task_rows in grouped.items():
        random.shuffle(task_rows)

        test_count = max(1, int(len(task_rows) * test_size))

        test_rows.extend(task_rows[:test_count])
        train_rows.extend(task_rows[test_count:])

    random.shuffle(train_rows)
    random.shuffle(test_rows)

    return train_rows, test_rows


def main():
    parser = argparse.ArgumentParser(description="Split JSONL instruction dataset into train/test sets.")

    parser.add_argument(
        "--input",
        type=str,
        default="data/instruction/finance_gold_v2.jsonl",
        help="Input combined JSONL dataset",
    )

    parser.add_argument(
        "--train-output",
        type=str,
        default="data/instruction/finance_gold_train.jsonl",
        help="Output train JSONL file",
    )

    parser.add_argument(
        "--test-output",
        type=str,
        default="data/instruction/finance_gold_test.jsonl",
        help="Output test JSONL file",
    )

    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data to use for test set",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    train_output = Path(args.train_output)
    test_output = Path(args.test_output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    rows = read_jsonl(input_path)

    if not rows:
        raise ValueError(f"No rows found in {input_path}")

    train_rows, test_rows = stratified_split(
        rows=rows,
        test_size=args.test_size,
        seed=args.seed,
    )

    write_jsonl(train_output, train_rows)
    write_jsonl(test_output, test_rows)

    print("=" * 80)
    print("Dataset split complete")
    print("=" * 80)
    print(f"Input file: {input_path}")
    print(f"Total rows: {len(rows)}")
    print(f"Train rows: {len(train_rows)}")
    print(f"Test rows: {len(test_rows)}")
    print()
    print("Full dataset task distribution:")
    print(dict(Counter(get_task(row) for row in rows)))
    print()
    print("Train task distribution:")
    print(dict(Counter(get_task(row) for row in train_rows)))
    print()
    print("Test task distribution:")
    print(dict(Counter(get_task(row) for row in test_rows)))
    print()
    print(f"Train saved to: {train_output}")
    print(f"Test saved to: {test_output}")


if __name__ == "__main__":
    main()