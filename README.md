# Finetuning Finance

Project scaffold for financial model finetuning.

## Finance AI Platform

A production-style project for fine-tuning and serving an LLM on financial data.

## Goal

Build an end-to-end finance AI platform covering:

* dataset curation
* QLoRA fine-tuning
* model evaluation
* vLLM inference
* quantization benchmarking
* FastAPI serving
* Prometheus/Grafana monitoring

## Architecture

See `reports/architecture.md`.

## Day 1 Status

* [x] Repo created
* [x] Project structure created
* [x] Financial PhraseBank download script added
* [x] Docker environment added
* [x] Architecture diagram v1 added

## Planned Stack

* Python
* Hugging Face Datasets
* Transformers
* PEFT
* bitsandbytes
* vLLM
* FastAPI
* Prometheus
* Grafana
* Docker

## Commands to Do Initial Setup

```bash
winget install Python.Python.3.11
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows PowerShell

pip install datasets pandas pyarrow
pip freeze > requirements.txt
```

## Run Locally

```bash
docker compose build --no-cache
docker compose up
docker ps
```

Open:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

## Day 3

### Run Cleaner Through Docker

```bash
docker compose run --rm data-cleaner
```

### Run API

```bash
docker compose up finance-ai-platform --build
```

### Create Sample File for Chunking

```powershell
echo Revenue increased by 18 percent due to stronger demand in cloud services. The company also reported higher operating expenses. > data\cleaned\sample.txt
```

### Run Chunking Script

```powershell
docker exec -it finance-ai-platform python src/data/chunk.py --input data/cleaned/sample.txt --output data/cleaned/sample_chunks.jsonl
```

### View Chunked Output

```powershell
docker exec -it finance-ai-platform cat data/cleaned/sample_chunks.jsonl
```

## Day 5: Add Instruction Dataset Preparation and Architecture Document

### Create Instructions

```powershell
docker exec -it finance-ai-platform python src/data/prepare_instruction_dataset.py --chunks data/cleaned/sample_chunks.jsonl --output data/instruction/sample_instruction_dataset.jsonl --task summarization
```

### Check Result

```powershell
docker exec -it finance-ai-platform cat data/instruction/sample_instruction_dataset.jsonl
```

## 90 Samples of Gold Dataset Combined

```powershell
docker exec -it finance-ai-platform python src/data/combine_gold_dataset.py --input-dir data/instruction/gold --output data/instruction/finance_gold_v1.jsonl --shuffle
```

### Check Combining

```powershell
docker exec -it finance-ai-platform python src/data/combine_gold_dataset.py --input-dir data/instruction/gold --output data/instruction/finance_gold_v1.jsonl --shuffle
```

## Model Setup for Training

```powershell
docker exec -it finance-ai-platform python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('Qwen/Qwen2.5-3B-Instruct'); print('Qwen2.5-3B tokenizer is available or downloaded successfully')"
```

### Check Whether the Model Files Are Already Cached Locally Inside Docker

```powershell
docker exec -it finance-ai-platform python -c "from huggingface_hub import scan_cache_dir; print(scan_cache_dir())"
```

### Try Loading the Model Config Without Loading Full Weights

```powershell
docker exec -it finance-ai-platform python -c "from transformers import AutoConfig; cfg=AutoConfig.from_pretrained('Qwen/Qwen2.5-3B-Instruct'); print(cfg.model_type); print(cfg.num_hidden_layers)"
```

### Run the Training Setup File

```powershell
docker exec -it finance-ai-platform python src/training/check_training_setup.py
```

### Run the Evaluation Setup

```powershell
docker exec -it finance-ai-platform python src/evaluation/check_eval_setup.py
```

### Run Local Training on Qwen2.5-3B-Instruct

```powershell
docker exec -it finance-ai-platform python src/training/train_qlora.py --model-name Qwen/Qwen2.5-3B-Instruct --dataset-path data/instruction/finance_gold_v1.jsonl --output-dir outputs/qlora-finance-v1 --max-steps 50 --max-length 512
```

## First QLoRA Run on 90 Samples

```text
Model: Qwen/Qwen2.5-3B-Instruct
Dataset: 90 gold examples
QLoRA: working
GPU: RTX 5060 Laptop GPU
Trainable params: 29.9M / 3.1B
Trainable %: 0.96%
Runtime: 121 seconds
Final train loss: ~1.004
Adapter saved: outputs/qlora-finance-v1
```

## Evaluation of the First Run

### Evaluate Fine-Tuned Adapter

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_v1.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --adapter-path outputs/qlora-finance-v1 --output-report reports/evaluation_finetuned_qwen3b.json --limit 10 --max-new-tokens 128
```

Example result:

```text
Metrics:
rouge1: 0.6265
rouge2: 0.4084
rougeL: 0.5627
rougeLsum: 0.5611
bertscore_precision: 0.9197
bertscore_recall: 0.9305
bertscore_f1: 0.9250
Evaluation report saved to: reports/evaluation_finetuned_qwen3b.json
```

### Evaluate Base Model for Comparison

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_v1.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --output-report reports/evaluation_base_qwen3b.json --limit 10 --max-new-tokens 128
```

Example result:

```text
Metrics:
rouge1: 0.1807
rouge2: 0.0860
rougeL: 0.1602
rougeLsum: 0.1593
bertscore_precision: 0.7571
bertscore_recall: 0.8317
bertscore_f1: 0.7898
Evaluation report saved to: reports/evaluation_base_qwen3b.json
================================================================================
Evaluation complete
=============================================
```

## Initial QLoRA Experiment Results

```text
Base model: Qwen2.5-3B-Instruct
Fine-tuning method: QLoRA
Dataset: 90 manually curated finance instruction examples
Training steps: 50
Max sequence length: 512
Trainable parameters: 29.9M / 3.1B, approximately 0.96%
```

Results:

* ROUGE-L improved from 0.1602 to 0.5627
* BERTScore F1 improved from 0.7898 to 0.9250

Interpretation:

The fine-tuned adapter produced outputs that were substantially closer to the target finance summaries, risk labels, and QA answers. Because this was an initial small-data experiment, a held-out test set is required for stronger generalization claims.

## Day 8: Increased Dataset Size to 300 Samples

Combined 100 samples from each task into a new file:

```powershell
docker exec -it finance-ai-platform python src/data/combine_gold_dataset.py --input-dir data/instruction/gold --output data/instruction/finance_gold_v2.jsonl --shuffle
```

### Count Number of Rows

```powershell
docker exec -it finance-ai-platform python -c "import json; p='data/instruction/finance_gold_v2.jsonl'; rows=[json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]; print(len(rows))"
```

### 80/20 Split

```powershell
docker exec -it finance-ai-platform python src/data/split_dataset.py --input data/instruction/finance_gold_v2.jsonl --train-output data/instruction/finance_gold_train.jsonl --test-output data/instruction/finance_gold_test.jsonl --test-size 0.2 --seed 42
```

```powershell
docker exec -it finance-ai-platform python src/data/split_dataset.py --input data/instruction/finance_gold_v1.jsonl --train-output data/instruction/finance_gold_train.jsonl --test-output data/instruction/finance_gold_test.jsonl --test-size 0.2 --seed 42
```

### Run Training on Train Set Only

```powershell
docker exec -it finance-ai-platform python src/training/train_qlora.py --model-name Qwen/Qwen2.5-3B-Instruct --dataset-path data/instruction/finance_gold_train.jsonl --output-dir outputs/qlora-finance-run2 --max-steps 150 --max-length 512
```

### Evaluate Base Model on Test Set

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --output-report reports/evaluation_base_qwen3b_run2_test.json --limit 60 --max-new-tokens 128
```

### Evaluate Fine-Tuned Adapter on Test Set

This evaluates Qwen + the LoRA adapter:

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --adapter-path outputs/qlora-finance-run2 --output-report reports/evaluation_finetuned_qwen3b_run1_test.json --limit 60 --max-new-tokens 128
```

### Test Run Result on Base Model Qwen2.5-3B-Instruct

```text
Metrics:
rouge1: 0.1944
rouge2: 0.0658
rougeL: 0.1610
rougeLsum: 0.1612
bertscore_precision: 0.7550
bertscore_recall: 0.8349
bertscore_f1: 0.7926
Evaluation report saved to: reports/evaluation_base_qwen3b_run2_test.json
```

## Hyperparameter Tuning

### Run A

Training time: `6+ minutes`

```powershell
docker exec -it finance-ai-platform python src/training/train_qlora.py --model-name Qwen/Qwen2.5-3B-Instruct --dataset-path data/instruction/finance_gold_train.jsonl --output-dir outputs/qlora-finance-runA-r8-lr2e4 --max-steps 150 --max-length 512 --learning-rate 2e-4 --lora-r 8 --lora-alpha 16 --gradient-accumulation-steps 4
```

### Run B

Training time: `18+ minutes`

```powershell
docker exec -it finance-ai-platform python src/training/train_qlora.py --model-name Qwen/Qwen2.5-3B-Instruct --dataset-path data/instruction/finance_gold_train.jsonl --output-dir outputs/qlora-finance-runB-r16-lr2e4 --max-steps 150 --max-length 512 --learning-rate 2e-4 --lora-r 16 --lora-alpha 32 --gradient-accumulation-steps 4
```

### Run C

Training time: `32+ minutes`

```powershell
docker exec -it finance-ai-platform python src/training/train_qlora.py --model-name Qwen/Qwen2.5-3B-Instruct --dataset-path data/instruction/finance_gold_train.jsonl --output-dir outputs/qlora-finance-runC-r16-lr1e4 --max-steps 150 --max-length 512 --learning-rate 1e-4 --lora-r 16 --lora-alpha 32 --gradient-accumulation-steps 4
```

## Evaluate Models After Hyperparameter Tuning

### Base Model

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --output-report reports/evaluation_base_qwen3b_day9_test.json --limit 60 --max-new-tokens 128
```

### Run A Evaluation

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --adapter-path outputs/qlora-finance-runA-r8-lr2e4 --output-report reports/evaluation_runA_r8_lr2e4.json --limit 60 --max-new-tokens 128
```

### Run B Evaluation

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --adapter-path outputs/qlora-finance-runB-r16-lr2e4 --output-report reports/evaluation_runB_r16_lr2e4.json --limit 60 --max-new-tokens 128
```

### Run C Evaluation

```powershell
docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --adapter-path outputs/qlora-finance-runC-r16-lr1e4 --output-report reports/evaluation_runC_r16_lr1e4.json --limit 60 --max-new-tokens 128
```

### Compare All Runs

```powershell
docker exec -it finance-ai-platform python src/evaluation/compare_reports.py --reports reports/evaluation_base_qwen3b_day9_test.json reports/evaluation_runA_r8_lr2e4.json reports/evaluation_runB_r16_lr2e4.json reports/evaluation_runC_r16_lr1e4.json --names Base RunA-r8-lr2e4 RunB-r16-lr2e4 RunC-r16-lr1e4 --output reports/evaluation_summary_day9.md
```

## Comparison Chart

| Metric            |   Base |  Run A |  **Run B** |  Run C |
| ----------------- | -----: | -----: | ---------: | -----: |
| ROUGE-1           | 0.1948 | 0.3989 | **0.4566** | 0.4077 |
| ROUGE-2           | 0.0655 | 0.1925 | **0.2489** | 0.1657 |
| ROUGE-L           | 0.1610 | 0.3321 | **0.3940** | 0.3334 |
| BERTScore F1      | 0.8751 | 0.9153 | **0.9237** | 0.9142 |
| Empty predictions |      0 |      0 |      **0** |      1 |

## Model Selection Summary

Run B was selected as the best fine-tuned model.

The key metric is **BERTScore F1**, because this project involves text generation tasks where semantic similarity matters. Run B achieved the highest BERTScore F1:

| Model | BERTScore F1 |
| ----- | -----------: |
| Run B |   **0.9237** |
| Run A |       0.9153 |
| Run C |       0.9142 |
| Base  |       0.8751 |

Run B also achieved the best **ROUGE-L**, which shows that its responses were closer to the reference answers in wording and structure:

| Model |    ROUGE-L |
| ----- | ---------: |
| Run B | **0.3940** |
| Run C |     0.3334 |
| Run A |     0.3321 |
| Base  |     0.1610 |

Run B performed better than Run A because it used a higher LoRA rank:

| Run   | LoRA Rank | Learning Rate |
| ----- | --------: | ------------: |
| Run A |         8 |          2e-4 |
| Run B |        16 |          2e-4 |

The higher LoRA rank gave the adapter more capacity to learn finance-specific response patterns.

Run B also performed better than Run C. Both used LoRA rank 16, but Run C used a lower learning rate:

| Run   | LoRA Rank | Learning Rate |
| ----- | --------: | ------------: |
| Run B |        16 |          2e-4 |
| Run C |        16 |          1e-4 |

Run C produced weaker scores and had one empty prediction, which suggests the lower learning rate may not have adapted the model enough within the same training budget.

## Improvement Over Base Model

| Metric       |   Base |  Run B | Improvement |
| ------------ | -----: | -----: | ----------: |
| ROUGE-1      | 0.1948 | 0.4566 |     +0.2618 |
| ROUGE-2      | 0.0655 | 0.2489 |     +0.1833 |
| ROUGE-L      | 0.1610 | 0.3940 |     +0.2330 |
| BERTScore F1 | 0.8751 | 0.9237 |     +0.0486 |

These results show that QLoRA fine-tuning improved the model on the held-out finance test set.

## Final Selected Adapter

```text
outputs/qlora-finance-runB-r16-lr2e4
```
# Day 11 - setting up the vLLM and running the llm qwen2.2-1.5B- instruct

added the server section for vLLM in the docker file
ran following commands::
    docker compose down
    docker compose up vllm-server

Test:
    curl.exe http://localhost:8001/v1/models

Response:

    {"object":"list","data":[{"id":"finance-qwen1.5b","object":"model","created":1781640354,"owned_by":"vllm","root":"Qwen/Qwen2.5-1.5B-Instruct","parent":null,"max_model_len":1024,"permission":[{"id":"modelperm-aedd9ed3e5e55381","object":"model_permission","created":1781640354,"allow_create_engine":false,"allow_sampling":true,"allow_logprobs":true,"allow_search_indices":false,"allow_view":true,"allow_fine_tuning":false,"organization":"*","group":null,"is_blocking":false}]}]}



## Day 11 Serving Result

The vLLM server was successfully deployed and tested through the OpenAI-compatible chat completion endpoint.

Served model:

```text
finance-qwen1.5b


Test endpoint: http://localhost:8001/v1/chat/completions

-- Qwen2.5-3B-Instruct was initially tested, but the local 8GB GPU did not have enough remaining memory for KV cache blocks after loading the model weights. For the Day 11 serving deliverable, Qwen2.5-1.5B-Instruct was used as the reliable local serving model.

## Benchmarking throughput and latency

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 128 --output reports/latency_benchmark_day12.json

python src/inference/benchmark_throughput.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 20 --concurrency 4 --max-tokens 128 --output reports/throughput_benchmark_day12.json

### inside docker (optional commands as above two)

docker exec -it finance-ai-platform python src/inference/benchmark_latency.py --base-url http://host.docker.internal:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 128 --output reports/latency_benchmark_day12.json

docker exec -it finance-ai-platform python src/inference/benchmark_throughput.py --base-url http://host.docker.internal:8001 --model finance-qwen1.5b --num-requests 20 --concurrency 4 --max-tokens 128 --output reports/throughput_benchmark_day12.json

### commands to use in sequence for benchmarking::

curl.exe http://localhost:8001/v1/models

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 128 --output reports/latency_benchmark_day12.json

python src/inference/benchmark_throughput.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 20 --concurrency 2 --max-tokens 128 --output reports/throughput_benchmark_day12_c2.json

python src/inference/benchmark_throughput.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 20 --concurrency 4 --max-tokens 128 --output reports/throughput_benchmark_day12_c4.json

## Day 13 Summary

Day 13 extended the initial Day 12 benchmark by testing different generation lengths and concurrency levels.

The latency experiments show the cost of generating longer responses. The throughput experiments show how vLLM handles multiple simultaneous finance prompts.

This benchmark helps identify a practical local serving configuration for the project. On the RTX 5060 Laptop GPU with ~8GB VRAM, `finance-qwen1.5b` is the reliable local vLLM serving model, while Qwen2.5-3B remains the local fine-tuning target.

commands ran::

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 64 --output reports/latency_day13_t64.json

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 128 --output reports/latency_day13_t128.json

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 256 --output reports/latency_day13_t256.json

throughput benchmarks::

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 64 --output reports/latency_day13_t64.json

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 128 --output reports/latency_day13_t128.json

python src/inference/benchmark_latency.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 10 --max-tokens 256 --output reports/latency_day13_t256.json

## concurrency::
python src/inference/benchmark_throughput.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 20 --concurrency 1 --max-tokens 128 --output reports/throughput_day13_c1.json

python src/inference/benchmark_throughput.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 20 --concurrency 2 --max-tokens 128 --output reports/throughput_day13_c2.json

python src/inference/benchmark_throughput.py --base-url http://localhost:8001 --model finance-qwen1.5b --num-requests 20 --concurrency 4 --max-tokens 128 --output reports/throughput_day13_c4.json

## Day 14 -  Quanization & Benchamarking

INT 8 -  quantization

docker exec -it finance-ai-platform python src/inference/benchmark_quantization.py --model-name Qwen/Qwen2.5-3B-Instruct --quantization int8 --num-requests 5 --max-new-tokens 128 --output reports/quantization_int8_day14.json

Notes;: Qwen2.5-3B loads with lower memory than FP16
Latency and tokens/sec are recorded
Report saved to reports/quantization_int8_day14.json

INT 4 - quantization

docker exec -it finance-ai-platform python src/inference/benchmark_quantization.py --model-name Qwen/Qwen2.5-3B-Instruct --quantization int4 --num-requests 5 --max-new-tokens 128 --output reports/quantization_int4_day14.json

fp16 - quantization

docker exec -it finance-ai-platform python src/inference/benchmark_quantization.py --model-name Qwen/Qwen2.5-3B-Instruct --quantization fp16 --num-requests 5 --max-new-tokens 128 --output reports/quantization_fp16_day14.json                                                  


--comparison report

docker exec -it finance-ai-platform python src/inference/compare_quantization_reports.py --reports FP16=reports/quantization_fp16_day14.json INT8=reports/quantization_int8_day14.json INT4=reports/quantization_int4_day14.json --output reports/quantization_comparison_day14.md

Day 15: Benchmarkign reports::

Batch size / concurrency vs throughput
Generation length vs latency
INT4 vs FP16
Memory vs latency
Final inference recommendation

command to run:

docker exec -it finance-ai-platform python src/inference/create_inference_benchmark_report.py --latency-reports t64=reports/latency_day13_t64.json t128=reports/latency_day13_t128.json t256=reports/latency_day13_t256.json --throughput-reports c1=reports/throughput_day13_c1.json c2=reports/throughput_day13_c2.json c4=reports/throughput_day13_c4.json --quantization-reports FP16=reports/quantization_fp16_day14.json INT8=reports/quantization_int8_day14.json INT4=reports/quantization_int4_day14.json --output reports/inference_benchmark_report.md

report is at : reports/inference_benchmark_report.md

### Day 16

docker compose up vllm-server
docker compose build finance-ai-platform
## to check the vllm :
curl.exe http://localhost:8001/v1/models

# to check if the fastapi is running:
curl.exe http://localhost:8000/health

Day 17: add /qa endpoint

Restart FastAPI::
docker compose restart finance-ai-platform
Make sure vLLM is running:
curl.exe http://localhost:8001/v1/models
Make sure FastAPI is running:
curl.exe http://localhost:8000/health

#### run load test::
python src/api/load_test_qa.py --base-url http://localhost:8000 --num-requests 5 --concurrency 1 --output reports/load_test_qa_day17_c1_small.json

python src/api/load_test_qa.py --base-url http://localhost:8000 --num-requests 20 --concurrency 1 --output reports/load_test_qa_day17_c1.json

python src/api/load_test_qa.py --base-url http://localhost:8000 --num-requests 20 --concurrency 2 --output reports/load_test_qa_day17_c2.json

python src/api/load_test_qa.py --base-url http://localhost:8000 --num-requests 20 --concurrency 4 --output reports/load_test_qa_day17_c4.json

day 18: 
docker compose restart finance-ai-platform
curl.exe http://localhost:8000/health
curl.exe http://localhost:8001/v1/models

python src/api/profile_api_performance.py --base-url http://localhost:8000 --num-requests 3 --concurrency 1 --output-json reports/api_profile_day18_small.json --output-md reports/api_profile_day18_small.md


python src/api/profile_api_performance.py --base-url http://localhost:8000 --num-requests 10 --concurrency 2 --output-json reports/api_performance_profile_day18.json --output-md reports/api_performance_profile_day18.md

python src/api/profile_api_performance.py --base-url http://localhost:8000 --num-requests 20 --concurrency 4 --output-json reports/api_performance_profile_day18_c4.json --output-md reports/api_performance_profile_day18_c4.md

### Day 19: add prometheus and grafana
docker compose up -d prometheus grafana

http://localhost:9090

Denerate traffic for the dashboard::
python src/api/profile_api_performance.py --base-url http://localhost:8000 --num-requests 10 --concurrency 2 --output-json reports/api_performance_profile_day19.json --output-md reports/api_performance_profile_day19.md

Day 20 - ENd to End test

docker compose up -d finance-ai-platform vllm-server prometheus grafana

Run end to end test: 

python src/api/end_to_end_test.py --api-base-url http://localhost:8000 --vllm-base-url http://localhost:8001 --prometheus-url http://localhost:9090 --output-json reports/end_to_end_day20.json --output-md reports/end_to_end_day20.md


Day 20 End-to-End Test
================================================================================
Overall status: PASSED
PASS - fastapi_health
PASS - fastapi_metrics
PASS - vllm_models
PASS - prometheus_ready
PASS - summarize
PASS - qa
PASS - risk_analysis
JSON report saved to: reports\end_to_end_day20.json
Markdown report saved to: reports\end_to_end_day20.md