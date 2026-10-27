"""Spark pipeline: detect PII with Presidio, pseudonymize, write output.
Use PII_DETECTOR_MODE=baseline or tuned to select detection rules."""
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

def pseudonymize_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    from pii_pipeline.detect import detect, resolve_overlaps
    mode = os.environ.get("PII_DETECTOR_MODE", "baseline")
    results = resolve_overlaps(detect(text, mode=mode))
    for r in results:
        text = text[:r.start] + token(r.entity_type, text[r.start:r.end]) + text[r.end:]
    return text

@pandas_udf(StringType())
def pseudonymize_udf(texts: pd.Series) -> pd.Series:
    return texts.map(pseudonymize_text)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--text-col", default="source_text")
    a = p.parse_args()
    opts = "-Dio.netty.tryReflectionSetAccessible=true"
    spark = (SparkSession.builder.appName("pii-pseudonymization")
             .master(os.environ.get("SPARK_MASTER", "local[*]"))
             .config("spark.driver.extraJavaOptions", opts)
             .config("spark.executor.extraJavaOptions", opts)
             .getOrCreate())
    df = spark.read.parquet(a.input)
    if a.limit:
        df = df.limit(a.limit)
    df.withColumn("pseudonymized", pseudonymize_udf(df[a.text_col])).write.mode("overwrite").parquet(a.output)

if __name__ == "__main__":
    main()
