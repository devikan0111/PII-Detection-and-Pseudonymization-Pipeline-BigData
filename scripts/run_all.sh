```bash
#!/usr/bin/env bash
set -euo pipefail

python scripts/download_data.py

python -m pii_pipeline.spark_job \
    --input data/raw/ai4privacy.parquet \
    --output data/processed/pseudonymized

python -m pii_pipeline.evaluate metrics --n 1000 --mode baseline

python -m pii_pipeline.evaluate metrics --n 1000 --mode tuned

python -m pii_pipeline.evaluate throughput --n 10000 --cores 1 2

python -m pii_pipeline.reidentify

echo "All pipeline steps completed successfully."
```
