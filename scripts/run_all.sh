#!/usr/bin/env bash
set -euo pipefail
python scripts/download_data.py
python -m pii_pipeline.spark_job --input data/raw/ai4privacy.parquet --output data/processed/pseudonymized
python -m pii_pipeline.evaluate
python -m pii_pipeline.reidentify
