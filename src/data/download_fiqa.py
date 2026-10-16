from datasets import load_dataset
import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw/fiqa")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def main():
    dataset = load_dataset("LLukas22/fiqa")

    print(dataset)

    for split_name, split_data in dataset.items():
        df = pd.DataFrame(split_data)
        output_path = RAW_DIR / f"{split_name}.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved {split_name}: {df.shape} -> {output_path}")
        print(df.head())

if __name__ == "__main__":
    main()