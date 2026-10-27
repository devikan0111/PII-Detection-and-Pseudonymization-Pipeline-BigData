"""Spark pipeline: detect PII with Presidio, pseudonymize, write output.
Skeleton - fill in TODOs as you build."""
import argparse, hmac, hashlib, os
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType

SECRET = os.environ.get("PSEUDO_SECRET", "change-me").encode()

def token(entity_type: str, value: str) -> str:
    """Keyed, deterministic pseudonym (HMAC) so the same person maps to the same token."""
    h = hmac.new(SECRET, f"{entity_type}:{value}".encode(), hashlib.sha256).hexdigest()[:10]
    return f"<{entity_type}_{h}>"

_analyzer = None
def get_analyzer():
    global _analyzer  # one Presidio engine per executor process
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        _analyzer = AnalyzerEngine()
    return _analyzer

def pseudonymize_text(text: str) -> str:
    results = sorted(get_analyzer().analyze(text=text, language="en",
             entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS"]), key=lambda r: r.start, reverse=True)
    for r in results:
        text = text[:r.start] + token(r.entity_type, text[r.start:r.end]) + text[r.end:]
    return text

@pandas_udf(StringType())
def pseudonymize_udf(texts: pd.Series) -> pd.Series:
    return texts.map(pseudonymize_text)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--text-col", default="source_text")
    a = p.parse_args()
    spark = SparkSession.builder.appName("pii-pseudonymization").master(os.environ.get("SPARK_MASTER", "local[*]")).getOrCreate()
    df = spark.read.parquet(a.input)
    df.withColumn("pseudonymized", pseudonymize_udf(df[a.text_col])).write.mode("overwrite").parquet(a.output)

if __name__ == "__main__":
    main()
