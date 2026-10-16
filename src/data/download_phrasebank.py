from datasets import load_dataset
from pathlib import Path

OUT_DIR = Path("data/raw/financial_phrasebank")
OUT_DIR.mkdir(parents=True, exist_ok=True)

dataset = load_dataset(
    "gtfintechlab/financial_phrasebank_sentences_allagree",
    "5768"
)

csv_path = OUT_DIR / "financial_phrasebank.csv"
dataset["train"].to_csv(csv_path, index=False)

print(dataset)
print(dataset["train"][0])
print(f"Saved to: {csv_path.resolve()}")