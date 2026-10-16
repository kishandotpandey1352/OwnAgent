import os
import torch
from transformers import AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig


def main():
    target_model = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
    local_test_model = os.getenv("LOCAL_TEST_MODEL", "Qwen/Qwen2.5-3B-Instruct")

    print("=" * 80)
    print("Day 6 Training Setup Check")
    print("=" * 80)

    print(f"Target model: {target_model}")
    print(f"Local test model: {local_test_model}")
    print()

    print("CUDA check")
    print(f"torch.cuda.is_available(): {torch.cuda.is_available()}")
    print(f"torch.cuda.device_count(): {torch.cuda.device_count()}")

    if torch.cuda.is_available():
        print(f"GPU name: {torch.cuda.get_device_name(0)}")
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU memory: {total_memory:.2f} GB")
    else:
        print("No GPU detected inside Docker.")
        print("Dependency checks can still run, but QLoRA training needs GPU.")
    print()

    print("Loading tokenizer")
    tokenizer = AutoTokenizer.from_pretrained(local_test_model)
    print("Tokenizer loaded successfully")
    print(f"Vocab size: {len(tokenizer)}")
    print()

    print("Creating BitsAndBytes 4-bit config")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    print(bnb_config)
    print()

    print("Creating LoRA config")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    print(lora_config)
    print()

    print("=" * 80)
    print("Training setup check passed")
    print("=" * 80)


if __name__ == "__main__":
    main()