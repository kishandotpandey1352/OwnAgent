from pathlib import Path
import json
import random
import argparse


REQUIRED_FIELDS = ["instruction", "input", "output"]


def validate_record(record: dict, source_file: Path, line_number: int):
    for field in REQUIRED_FIELDS:
        if field not in record:
            raise ValueError(
                f"Missing field '{field}' in {source_file} at line {line_number}"
            )

        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(
                f"Field '{field}' is empty or invalid in {source_file} at line {line_number}"
            )


def read_jsonl(path: Path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            record = json.loads(line)
            validate_record(record, path, line_number)

            if "metadata" not in record:
                record["metadata"] = {}

            record["metadata"]["source_file"] = path.name

            records.append(record)

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Combine gold JSONL datasets into one training file."
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/instruction/gold",
        help="Directory containing category JSONL files",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/instruction/finance_gold_v1.jsonl",
        help="Output combined JSONL file",
    )

    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle records before saving",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffling",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    jsonl_files = sorted(input_dir.glob("*.jsonl"))

    if not jsonl_files:
        raise FileNotFoundError(f"No JSONL files found in {input_dir}")

    all_records = []

    print("Combining files:")

    for file_path in jsonl_files:
        records = read_jsonl(file_path)
        all_records.extend(records)
        print(f"- {file_path}: {len(records)} records")

    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(all_records)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print()
    print(f"Total records: {len(all_records)}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()