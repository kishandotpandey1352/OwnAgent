# Provider failure
Use bounded retries with jitter and circuit breakers. Use fallback only if that provider/model has passed the same task evaluation. Otherwise fail safely or degrade optional work.
