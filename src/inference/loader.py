import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import boto3
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


class FinanceLLM:
    def __init__(self) -> None:
        self.base_model_name = os.getenv("BASE_MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct")
        self.adapter_s3_uri = os.getenv("ADAPTER_S3_URI", "")
        self.model_id = os.getenv("MODEL_ID", "qwen2.5-3b-finance-runB-r16-lr2e4")
        self.load_in_4bit = os.getenv("LOAD_IN_4BIT", "true").lower() == "true"
        self.device_map = os.getenv("DEVICE_MAP", "auto")

        self.adapter_local_dir = Path("/tmp/qwen2.5-3b-finance-adapter")

        self.tokenizer = None
        self.model = None

        self.model_loaded = False
        self.adapter_loaded = False

    def _download_s3_prefix(self, s3_uri: str, local_dir: Path) -> None:
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")

        no_scheme = s3_uri.replace("s3://", "", 1)
        bucket, prefix = no_scheme.split("/", 1)
        prefix = prefix.rstrip("/") + "/"

        if local_dir.exists():
            shutil.rmtree(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)

        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")

        found = False
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue

                rel_path = key[len(prefix):]
                if not rel_path:
                    continue

                dest = local_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(bucket, key, str(dest))
                found = True

        if not found:
            raise FileNotFoundError(f"No adapter files found at {s3_uri}")

    def load(self) -> None:
        if self.model_loaded and self.adapter_loaded:
            return

        print("Loading tokenizer...", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name,
            trust_remote_code=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        quantization_config: Optional[BitsAndBytesConfig] = None
        if self.load_in_4bit:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )

        print("Loading base model...", flush=True)
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            quantization_config=quantization_config,
            device_map=self.device_map,
            trust_remote_code=True,
        )

        self.model_loaded = True

        if not self.adapter_s3_uri:
            raise ValueError("ADAPTER_S3_URI is not set.")

        print(f"Downloading adapter from {self.adapter_s3_uri}...", flush=True)
        self._download_s3_prefix(self.adapter_s3_uri, self.adapter_local_dir)

        print("Loading LoRA adapter...", flush=True)
        self.model = PeftModel.from_pretrained(
            base_model,
            str(self.adapter_local_dir),
        )
        self.model.eval()

        self.adapter_loaded = True
        print("Finance LLM loaded successfully.", flush=True)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 128,
        temperature: float = 0.2,
    ) -> str:
        self.load()

        assert self.model is not None
        assert self.tokenizer is not None

        messages = [
            {
                "role": "system",
                "content": "You are a financial analysis assistant. Be concise, accurate, and practical.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        if hasattr(self.tokenizer, "apply_chat_template"):
            input_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            input_text = prompt

        inputs = self.tokenizer(input_text, return_tensors="pt")

        if hasattr(self.model, "device"):
            inputs = {key: value.to(self.model.device) for key, value in inputs.items()}

        do_sample = temperature > 0

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if do_sample else None,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
        output = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

        return output.strip()


_finance_llm: Optional[FinanceLLM] = None


def get_finance_llm() -> FinanceLLM:
    global _finance_llm

    if _finance_llm is None:
        _finance_llm = FinanceLLM()

    return _finance_llm
