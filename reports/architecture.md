# Finance AI Platform Architecture v1

```mermaid
flowchart TD
    A[Financial Datasets] --> B[Data Cleaning]
    B --> C[Instruction Dataset]
    C --> D[QLoRA Fine-Tuning]
    D --> E[Evaluation Suite]
    E --> F[vLLM Inference Server]
    F --> G[FastAPI Service]
    G --> H[Prometheus Metrics]
    H --> I[Grafana Dashboard]

    E --> J[Reports]
    F --> K[Benchmarking]
    K --> J