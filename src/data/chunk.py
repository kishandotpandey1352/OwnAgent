from pathlib import Path
import json
import argparse


def read_text_file(path: Path) -> str:
    """
    Reads text files with common encodings.
    PowerShell-created files are often UTF-16.
    """
    encodings = ["utf-8", "utf-8-sig", "utf-16", "latin-1"]

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Unable to decode file: {path}")


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200):
    """
    Splits long text into overlapping chunks.
    Character-based for now.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def chunk_file(input_path: Path, output_path: Path, chunk_size: int, overlap: int):
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    text = read_text_file(input_path)

    chunks = chunk_text(
        text=text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for idx, chunk in enumerate(chunks):
            record = {
                "source_file": input_path.name,
                "chunk_id": idx,
                "chunk_size": len(chunk),
                "text": chunk,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    print(f"Chunks created: {len(chunks)}")


def main():
    parser = argparse.ArgumentParser(description="Chunk cleaned financial text files.")

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to cleaned input text file",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/cleaned/chunks.jsonl",
        help="Path to output JSONL chunks file",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1200,
        help="Chunk size in characters",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Overlap between chunks in characters",
    )

    args = parser.parse_args()

    chunk_file(
        input_path=Path(args.input),
        output_path=Path(args.output),
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )


if __name__ == "__main__":
    main()