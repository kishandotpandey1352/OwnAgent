# Day 9 Evaluation Summary

## Experiment Setup

Base model: `Qwen/Qwen2.5-3B-Instruct`  
Fine-tuning method: QLoRA  
Dataset: Finance gold dataset  
Train examples: 240  
Test examples: 60  
Evaluation set: `data/instruction/finance_gold_test.jsonl`  

## Compared Runs

| Run | Report File |
|---|---|
| Base | `reports/evaluation_base_qwen3b_day9_test.json` |
| RunA-r8-lr2e4 | `reports/evaluation_runA_r8_lr2e4.json` |
| RunB-r16-lr2e4 | `reports/evaluation_runB_r16_lr2e4.json` |
| RunC-r16-lr1e4 | `reports/evaluation_runC_r16_lr1e4.json` |

## Metrics

| Model / Run | ROUGE-1 | ROUGE-2 | ROUGE-L | ROUGE-Lsum | BERTScore Precision | BERTScore Recall | BERTScore F1 | Empty Predictions | Empty References |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Base | 0.1948 | 0.0655 | 0.1610 | 0.1607 | 0.8484 | 0.9039 | 0.8751 | 0 | 0 |
| RunA-r8-lr2e4 | 0.3989 | 0.1925 | 0.3321 | 0.3334 | 0.9057 | 0.9256 | 0.9153 | 0 | 0 |
| RunB-r16-lr2e4 | 0.4566 | 0.2489 | 0.3940 | 0.3981 | 0.9181 | 0.9296 | 0.9237 | 0 | 0 |
| RunC-r16-lr1e4 | 0.4077 | 0.1657 | 0.3334 | 0.3365 | 0.9079 | 0.9210 | 0.9142 | 1 | 0 |

## Best Run

Best run by BERTScore F1: **RunB-r16-lr2e4**  
BERTScore F1: **0.9237**  
ROUGE-L: **0.3940**  

## Interpretation

This report compares the base model against multiple QLoRA adapters trained with different hyperparameter settings. All models are evaluated on the same held-out finance test set, so the comparison is fair as long as all JSON reports were generated using the same evaluation script.

The selected best run is based primarily on BERTScore F1, with ROUGE-L used as a secondary signal. Empty prediction counts are included because a model that produces blank or invalid outputs should not be selected even if some metrics appear competitive.
