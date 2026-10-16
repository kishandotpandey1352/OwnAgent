import argparse
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)


REQUIRED_FIELDS = ["instruction", "input", "output"]


def set_seed(seed: int) -> None:
    """
    Make training more reproducible.
    Exact reproducibility is not guaranteed across GPU/CUDA versions,
    but this helps keep runs more stable.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def validate_record(record: dict, line_number: int, path: str) -> None:
    """
    Validate one instruction-tuning record.
    Expected schema:
    {
      "instruction": "...",
      "input": "...",
      "output": "...",
      "metadata": {...}
    }
    """
    for field in REQUIRED_FIELDS:
        if field not in record:
            raise ValueError(
                f"Missing required field '{field}' at line {line_number} in {path}"
            )

        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(
                f"Field '{field}' is empty or invalid at line {line_number} in {path}"
            )


def load_jsonl_dataset(path: str) -> Dataset:
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            record = json.loads(line)
            validate_record(record, line_number, path)
            records.append(record)

    if not records:
        raise ValueError(f"No records found in {path}")

    return Dataset.from_list(records)


def format_prompt(example: dict) -> str:
    """
    Training format.

    The model sees:
    - instruction
    - input/context
    - expected response

    During training, labels are the same as input_ids, so the model learns
    to generate the full formatted text. This is simple and works for an
    early QLoRA project.
    """
    instruction = example["instruction"].strip()
    input_text = example["input"].strip()
    output = example["output"].strip()

    prompt = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Response:
{output}"""

    return prompt


def tokenize_dataset(dataset: Dataset, tokenizer, max_length: int) -> Dataset:
    def tokenize(example):
        text = format_prompt(example)

        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding=False,
        )

        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    return dataset.map(
        tokenize,
        remove_columns=dataset.column_names,
        desc="Tokenizing dataset",
    )


def create_bnb_config(compute_dtype: str):
    dtype_map = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }

    if compute_dtype not in dtype_map:
        raise ValueError("compute_dtype must be either 'float16' or 'bfloat16'")

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=dtype_map[compute_dtype],
        bnb_4bit_use_double_quant=True,
    )


def create_lora_config(
    lora_r: int,
    lora_alpha: int,
    lora_dropout: float,
):
    return LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )


def print_gpu_info() -> None:
    print(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        total_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU memory: {total_memory_gb:.2f} GB")
    else:
        print("No GPU detected. QLoRA training is expected to be very slow or fail.")


def main():
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning script")

    parser.add_argument(
        "--model-name",
        type=str,
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Base model name",
    )

    parser.add_argument(
        "--dataset-path",
        type=str,
        default="data/instruction/finance_gold_train.jsonl",
        help="Path to JSONL instruction training dataset",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/qlora-finance",
        help="Directory to save LoRA adapter",
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Max sequence length",
    )

    parser.add_argument(
        "--epochs",
        type=float,
        default=1.0,
        help="Number of training epochs",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=150,
        help="Max training steps. Use -1 to train for full epochs.",
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="Learning rate",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Per-device train batch size",
    )

    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=4,
        help="Gradient accumulation steps",
    )

    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="LoRA rank",
    )

    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=32,
        help="LoRA alpha",
    )

    parser.add_argument(
        "--lora-dropout",
        type=float,
        default=0.05,
        help="LoRA dropout",
    )

    parser.add_argument(
        "--warmup-ratio",
        type=float,
        default=0.03,
        help="Warmup ratio",
    )

    parser.add_argument(
        "--weight-decay",
        type=float,
        default=0.0,
        help="Weight decay",
    )

    parser.add_argument(
        "--logging-steps",
        type=int,
        default=1,
        help="Logging frequency",
    )

    parser.add_argument(
        "--save-steps",
        type=int,
        default=25,
        help="Checkpoint save frequency",
    )

    parser.add_argument(
        "--save-total-limit",
        type=int,
        default=2,
        help="Maximum number of checkpoints to keep",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )

    parser.add_argument(
        "--compute-dtype",
        type=str,
        default="float16",
        choices=["float16", "bfloat16"],
        help="Compute dtype for 4-bit quantized training",
    )

    parser.add_argument(
        "--resume-from-checkpoint",
        type=str,
        default=None,
        help="Optional checkpoint path to resume training from",
    )

    parser.add_argument(
        "--report-to",
        type=str,
        default="none",
        help="Trainer reporting target. Use 'none' locally, or 'mlflow' later.",
    )

    args = parser.parse_args()

    set_seed(args.seed)

    hf_token = os.getenv("HF_TOKEN")

    print("=" * 80)
    print("QLoRA Training")
    print("=" * 80)
    print(f"Model: {args.model_name}")
    print(f"Dataset: {args.dataset_path}")
    print(f"Output dir: {args.output_dir}")
    print(f"HF token available: {bool(hf_token)}")
    print_gpu_info()

    print("\nHyperparameters:")
    print(f"Max length: {args.max_length}")
    print(f"Epochs: {args.epochs}")
    print(f"Max steps: {args.max_steps}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Batch size: {args.batch_size}")
    print(f"Gradient accumulation steps: {args.gradient_accumulation_steps}")
    print(f"Effective batch size: {args.batch_size * args.gradient_accumulation_steps}")
    print(f"LoRA r: {args.lora_r}")
    print(f"LoRA alpha: {args.lora_alpha}")
    print(f"LoRA dropout: {args.lora_dropout}")
    print(f"Warmup ratio: {args.warmup_ratio}")
    print(f"Weight decay: {args.weight_decay}")
    print(f"Compute dtype: {args.compute_dtype}")
    print(f"Seed: {args.seed}")

    dataset = load_jsonl_dataset(args.dataset_path)
    print(f"\nLoaded dataset with {len(dataset)} records")

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        token=hf_token,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "right"

    bnb_config = create_bnb_config(compute_dtype=args.compute_dtype)

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        token=hf_token,
    )

    model.config.use_cache = False

    try:
        model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False}
        )
    except TypeError:
        model.gradient_checkpointing_enable()

    model = prepare_model_for_kbit_training(model)

    lora_config = create_lora_config(
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
    )

    model = get_peft_model(model, lora_config)

    print("\nTrainable parameters:")
    model.print_trainable_parameters()

    tokenized_dataset = tokenize_dataset(
        dataset=dataset,
        tokenizer=tokenizer,
        max_length=args.max_length,
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    fp16 = args.compute_dtype == "float16"
    bf16 = args.compute_dtype == "bfloat16"

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        fp16=fp16,
        bf16=bf16,
        optim="paged_adamw_8bit",
        report_to=args.report_to,
        remove_unused_columns=False,
        gradient_checkpointing=True,
        max_grad_norm=1.0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    print("=" * 80)
    print("Training complete")
    print(f"LoRA adapter saved to: {args.output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()

