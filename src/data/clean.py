import argparse
import re
from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")


def normalize_text(text: str) -> str:
    text = str(text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_phrasebank() -> None:
    input_path = RAW_DIR / "financial_phrasebank" / "financial_phrasebank.csv"
    output_path = CLEANED_DIR / "financial_phrasebank_cleaned.csv"

    if not input_path.exists():
        print(f"Skipping PhraseBank. Missing: {input_path}")
        return

    df = pd.read_csv(input_path)

    text_col = "sentence" if "sentence" in df.columns else df.columns[0]
    df[text_col] = df[text_col].apply(normalize_text)

    before = len(df)
    df = df.drop_duplicates(subset=[text_col])
    df = df[df[text_col].str.len() > 20]
    after = len(df)

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"PhraseBank cleaned: {before} -> {after}")
    print(f"Saved: {output_path}")


def clean_fiqa() -> None:
    fiqa_dir = RAW_DIR / "fiqa"
    output_path = CLEANED_DIR / "fiqa_cleaned.csv"

    if not fiqa_dir.exists():
        print(f"Skipping FiQA. Missing: {fiqa_dir}")
        return

    frames = []

    for file_name in ["train.csv", "test.csv"]:
        file_path = fiqa_dir / file_name

        if file_path.exists():
            df = pd.read_csv(file_path)
            df["split"] = file_name.replace(".csv", "")
            frames.append(df)

    if not frames:
        print("No FiQA CSV files found.")
        return

    df = pd.concat(frames, ignore_index=True)

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(normalize_text)

    before = len(df)
    df = df.drop_duplicates()
    after = len(df)

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"FiQA cleaned: {before} -> {after}")
    print(f"Saved: {output_path}")


def clean_sec_filings() -> None:
    sec_dir = RAW_DIR / "sec" / "sec-edgar-filings"
    output_path = CLEANED_DIR / "sec_filings_cleaned.csv"

    if not sec_dir.exists():
        print(f"Skipping SEC filings. Missing: {sec_dir}")
        return

    rows = []

    for file_path in sec_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in [".txt", ".html", ".htm"]:
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                text = normalize_text(text)

                if len(text) > 500:
                    rows.append(
                        {
                            "source_file": str(file_path),
                            "company": extract_company_from_path(file_path),
                            "filing_type": extract_filing_type_from_path(file_path),
                            "text": text,
                            "char_count": len(text),
                        }
                    )

            except Exception as error:
                print(f"Failed reading {file_path}: {error}")

    if not rows:
        print("No SEC filing text found.")
        return

    df = pd.DataFrame(rows)

    before = len(df)
    df = df.drop_duplicates(subset=["text"])
    after = len(df)

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"SEC filings cleaned: {before} -> {after}")
    print(f"Saved: {output_path}")


def extract_company_from_path(file_path: Path) -> str:
    parts = file_path.parts

    for ticker in ["AAPL", "MSFT", "NVDA", "JPM", "GS"]:
        if ticker in parts:
            return ticker

    return "unknown"


def extract_filing_type_from_path(file_path: Path) -> str:
    parts = file_path.parts

    for filing_type in ["10-K", "10-Q", "8-K"]:
        if filing_type in parts:
            return filing_type

    return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw financial datasets.")

    parser.add_argument(
        "--dataset",
        choices=["all", "phrasebank", "fiqa", "sec"],
        default="all",
        help="Dataset to clean.",
    )

    args = parser.parse_args()

    if args.dataset in ["all", "phrasebank"]:
        clean_phrasebank()

    if args.dataset in ["all", "fiqa"]:
        clean_fiqa()

    if args.dataset in ["all", "sec"]:
        clean_sec_filings()


if __name__ == "__main__":
    main()