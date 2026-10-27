"""Download public datasets (no real personal data). Run: python scripts/download_data.py"""
from datasets import load_dataset
import pathlib

out = pathlib.Path("data/raw"); out.mkdir(parents=True, exist_ok=True)

# Labeled synthetic PII -> used for precision / recall (ground truth spans)
ds = load_dataset("ai4privacy/pii-masking-200k", split="train")
ds.to_parquet(out / "ai4privacy.parquet")

# Customer-support text -> used for throughput / scale tests
ds2 = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset", split="train")
ds2.to_parquet(out / "bitext_support.parquet")
print("done")
