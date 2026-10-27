"""Evaluate PII detection quality and Spark throughput.

Run from the repo root with PYTHONPATH=src:
  python -m pii_pipeline.evaluate metrics --n 1000 --mode baseline
  python -m pii_pipeline.evaluate metrics --n 1000 --mode tuned
  python -m pii_pipeline.evaluate throughput --n 2000 --cores 1 2 4

metrics    -> results/metrics_<mode>.csv, results/error_examples_<mode>.csv
throughput -> results/throughput.csv
Only English rows of ai4privacy (synthetic data) are used.
"""
import argparse, os, subprocess, sys, time
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/ai4privacy.parquet")
RESULTS = Path("results")
ENTITIES = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS"]

# ai4privacy label -> Presidio entity. Names are split into first/last/middle in the dataset.
# NOTE: ai4privacy merges phone numbers and IMEIs into one label (PHONEIMEI).
LABEL_TO_ENTITY = {
    "FIRSTNAME": "PERSON", "LASTNAME": "PERSON", "MIDDLENAME": "PERSON",
    "GIVENNAME": "PERSON", "SURNAME": "PERSON",
    "EMAIL": "EMAIL_ADDRESS",
    "PHONENUMBER": "PHONE_NUMBER", "PHONEIMEI": "PHONE_NUMBER",
}


# ---------- scoring (pure functions, unit-tested) ----------
def gold_spans(privacy_mask):
    """privacy_mask: list of {'value','start','end','label'} -> [(start, end, entity)] for mapped labels."""
    out = []
    for m in (privacy_mask if privacy_mask is not None else []):
        ent = LABEL_TO_ENTITY.get(m["label"])
        if ent:
            out.append((int(m["start"]), int(m["end"]), ent))
    return out


def _overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def score_doc(gold, pred):
    """gold/pred: lists of (start, end, entity). Returns {(mode, entity): [n_pred, pred_correct, n_gold, gold_found]}.

    overlap mode: a prediction is correct if it overlaps a gold span of the same entity
                  (so 'Kattie Smith' vs separate first/last name labels still counts).
    exact mode:   the (start, end) must match exactly.
    """
    res = {}
    for ent in ENTITIES:
        g = [(s, e) for s, e, t in gold if t == ent]
        p = [(s, e) for s, e, t in pred if t == ent]
        res[("overlap", ent)] = [
            len(p),
            sum(any(_overlap(x, y) for y in g) for x in p),
            len(g),
            sum(any(_overlap(y, x) for x in p) for y in g),
        ]
        hit = len(set(p) & set(g))
        res[("exact", ent)] = [len(p), hit, len(g), hit]

        # Maximum one-to-one overlap matching: each span is used at most once.
        edges = [
            [j for j, gold_span in enumerate(g) if _overlap(pred_span, gold_span)]
            for pred_span in p
        ]
        matched = {}

        def assign(i, seen):
            for j in edges[i]:
                if j in seen:
                    continue
                seen.add(j)
                if j not in matched or assign(matched[j], seen):
                    matched[j] = i
                    return True
            return False

        for i in range(len(p)):
            assign(i, set())

        hits = len(matched)
        res[("one_to_one", ent)] = [len(p), hits, len(g), hits]
    return res


def aggregate(per_doc_scores):
    total = {}
    for sc in per_doc_scores:
        for k, v in sc.items():
            t = total.setdefault(k, [0, 0, 0, 0])
            for i in range(4):
                t[i] += v[i]
    return total


def to_table(total):
    rows = []
    for mode in ("overlap", "exact", "one_to_one"):
        sums = [0, 0, 0, 0]
        for ent in ENTITIES + ["ALL"]:
            v = sums if ent == "ALL" else total.get((mode, ent), [0, 0, 0, 0])
            if ent != "ALL":
                sums = [a + b for a, b in zip(sums, v)]
            npred, pc, ngold, gf = v
            prec = pc / npred if npred else float("nan")
            rec = gf / ngold if ngold else float("nan")
            f1 = 2 * prec * rec / (prec + rec) if prec == prec and rec == rec and (prec + rec) else float("nan")
            rows.append(dict(mode=mode, entity=ent, predicted=npred, correct_predictions=pc,
                             gold=ngold, found_gold=gf,
                             precision=round(prec, 4), recall=round(rec, 4), f1=round(f1, 4)))
    return pd.DataFrame(rows)


# ---------- metrics command ----------
def load_english(n, seed):
    df = pd.read_parquet(RAW)
    df = df[df["language"] == "en"]
    return df.sample(n=min(n, len(df)), random_state=seed).reset_index(drop=True)


def cmd_metrics(a):
    from pii_pipeline.detect import detect
    df = load_english(a.n, a.seed)

    unmapped = {}
    for pm in df["privacy_mask"]:
        for m in (pm if pm is not None else []):
            if m["label"] not in LABEL_TO_ENTITY:
                unmapped[m["label"]] = unmapped.get(m["label"], 0) + 1
    print("Ground-truth labels NOT evaluated (not names/phones/emails):",
          dict(sorted(unmapped.items(), key=lambda kv: -kv[1])[:15]))

    scores, errors = [], []
    t0 = time.perf_counter()
    for text, pm in zip(df["source_text"], df["privacy_mask"]):
        gold = gold_spans(pm)
        pred = [(r.start, r.end, r.entity_type) for r in detect(text, mode=a.mode)]
        scores.append(score_doc(gold, pred))
        if len(errors) < 200:
            for s, e, t in gold:   # missed (leaked) PII
                if not any(_overlap((s, e), (ps, pe)) and t == pt for ps, pe, pt in pred):
                    errors.append(dict(kind="missed(FN)", entity=t, value=text[s:e], text=text))
            for s, e, t in pred:   # spurious detections
                if not any(_overlap((s, e), (gs, ge)) and t == gt for gs, ge, gt in gold):
                    errors.append(dict(kind="spurious(FP)", entity=t, value=text[s:e], text=text))
    secs = time.perf_counter() - t0

    RESULTS.mkdir(exist_ok=True)
    table = to_table(aggregate(scores))
    table.to_csv(RESULTS / f"metrics_{a.mode}.csv", index=False)
    pd.DataFrame(errors, columns=["kind", "entity", "value", "text"]).to_csv(
        RESULTS / f"error_examples_{a.mode}.csv", index=False)
    print(table.to_string(index=False))
    print(f"\n{len(df)} English documents, {secs:.1f}s single-process ({len(df)/secs:.1f} docs/s)")
    print(f"Saved results/metrics_{a.mode}.csv and results/error_examples_{a.mode}.csv")


# ---------- throughput command ----------
def write_parts(df, out_dir, parts):
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.parquet"):
        f.unlink()
    bounds = np.linspace(0, len(df), parts + 1, dtype=int)
    for i in range(parts):
        df.iloc[bounds[i]:bounds[i + 1]][["source_text"]].to_parquet(out_dir / f"part-{i:03d}.parquet", index=False)


def run_spark(cores, in_dir, out_dir):
    env = {**os.environ, "SPARK_MASTER": f"local[{cores}]", "PII_DETECTOR_MODE": "baseline"}
    cmd = [sys.executable, "-m", "pii_pipeline.spark_job", "--input", str(in_dir), "--output", str(out_dir)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    secs = time.perf_counter() - t0
    if p.returncode != 0:
        print(p.stderr[-3000:])
        raise SystemExit("Spark job failed")
    return secs


def cmd_throughput(a):
    df = load_english(a.n, a.seed)
    base = Path("data/processed")
    write_parts(df, base / "tp_input", 16)             # 16 files -> 16 Spark partitions
    write_parts(df.head(16), base / "tp_tiny", 4)      # tiny run = Spark + model start-up cost
    rows = []
    for cores in a.cores:
        startup = run_spark(cores, base / "tp_tiny", base / "tp_out")
        wall = run_spark(cores, base / "tp_input", base / "tp_out")
        net = max(wall - startup, 1e-9)
        rows.append(dict(cores=cores, rows=len(df), wall_seconds=round(wall, 1),
                         startup_seconds=round(startup, 1), net_seconds=round(net, 1),
                         rows_per_sec=round(len(df) / net, 2)))
        print(rows[-1])
    out = pd.DataFrame(rows)
    out["speedup_vs_first"] = (out["rows_per_sec"] / out["rows_per_sec"].iloc[0]).round(2)
    RESULTS.mkdir(exist_ok=True)
    out.to_csv(RESULTS / "throughput.csv", index=False)
    print(out.to_string(index=False))
    print("Saved results/throughput.csv")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("metrics"); m.add_argument("--n", type=int, default=1000); m.add_argument("--seed", type=int, default=42)
    m.add_argument("--mode", choices=["baseline", "tuned"], default="baseline")
    t = sub.add_parser("throughput"); t.add_argument("--n", type=int, default=2000); t.add_argument("--seed", type=int, default=42)
    t.add_argument("--cores", type=int, nargs="+", default=[1, 2, 4])
    a = p.parse_args()
    {"metrics": cmd_metrics, "throughput": cmd_throughput}[a.cmd](a)


if __name__ == "__main__":
    main()
