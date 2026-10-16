from pathlib import Path
import json
import argparse


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def create_instruction_record(chunk: dict, task: str):
    text = chunk["text"]

    if task == "summarization":
        instruction = "Summarize the following financial text clearly and concisely."
        output = "Summary not available yet. Replace this with a human-written or generated reference summary."

    elif task == "risk_analysis":
        instruction = "Identify the key financial or business risks in the following text."
        output = "Risks not available yet. Replace this with labelled risk information."

    elif task == "financial_qa":
        instruction = "Answer a finance-related question using the provided context."
        output = "Answer not available yet. Replace this with a reference answer."

    else:
        raise ValueError(f"Unsupported task: {task}")

    return {
        "instruction": instruction,
        "input": text,
        "output": output,
        "metadata": {
            "source_file": chunk.get("source_file"),
            "chunk_id": chunk.get("chunk_id"),
            "task": task,
        },
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--chunks",
        type=str,
        required=True,
        help="Input chunked JSONL file",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/instruction/instruction_dataset.jsonl",
        help="Output instruction JSONL file",
    )

    parser.add_argument(
        "--task",
        type=str,
        default="summarization",
        choices=["summarization", "risk_analysis", "financial_qa"],
    )

    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0

    with output_path.open("w", encoding="utf-8") as f:
        for chunk in read_jsonl(chunks_path):
            record = create_instruction_record(chunk, args.task)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"Created {count} instruction records")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()