import os

os.environ.setdefault("PSEUDO_SECRET", "test-only-secret-for-unit-tests")
from pii_pipeline.spark_job import token

def test_deterministic():
    assert token("PERSON", "Alice") == token("PERSON", "Alice")

def test_differs():
    assert token("PERSON", "Alice") != token("PERSON", "Bob")
def test_multiple_pii_replacements(monkeypatch):
    from pii_pipeline import spark_job
    from pii_pipeline import detect as detect_module
    from presidio_analyzer import RecognizerResult

    text = "Contact a@b.co or longperson@example.com."

    fake_results = [
        RecognizerResult("EMAIL_ADDRESS", 8, 14, 0.99),
        RecognizerResult("EMAIL_ADDRESS", 18, 40, 0.99),
    ]

    monkeypatch.setattr(
        detect_module, "detect",
        lambda text, mode="baseline": fake_results
    )
    monkeypatch.setattr(
        detect_module, "resolve_overlaps",
        lambda results: results
    )

    result = spark_job.pseudonymize_text(text)

    assert result == (
        f"Contact {spark_job.token('EMAIL_ADDRESS', 'a@b.co')} "
        f"or {spark_job.token('EMAIL_ADDRESS', 'longperson@example.com')}."
    )
def test_dictionary_attack_success_rate():
    from pii_pipeline.reidentify import evaluate_dictionary_attack

    originals = [
        "alice@example.com",
        "bob@example.com",
        "charlie@example.com",
        "david@example.com",
        "eve@example.com",
    ]

    candidates = originals[:4]

    correct_key = b"experiment-only-secret"
    wrong_key = b"attacker-wrong-secret"

    correct_count, correct_rate = evaluate_dictionary_attack(
        originals, candidates, correct_key, correct_key
    )

    wrong_count, wrong_rate = evaluate_dictionary_attack(
        originals, candidates, correct_key, wrong_key
    )

    assert correct_count == 4
    assert correct_rate == 80.0

    assert wrong_count == 0
    assert wrong_rate == 0.0

def test_missed_pii_analysis():
    import pandas as pd
    from pii_pipeline.reidentify import missed_pii_analysis

    metrics = pd.DataFrame([
        {
            "mode": "one_to_one",
            "entity": "PERSON",
            "gold": 100,
            "found_gold": 75,
        },
        {
            "mode": "one_to_one",
            "entity": "EMAIL_ADDRESS",
            "gold": 50,
            "found_gold": 50,
        },
    ])

    result = missed_pii_analysis(metrics)

    assert result.iloc[0]["missed_pii"] == 25
    assert result.iloc[0]["miss_rate_percent"] == 25.0

    assert result.iloc[1]["missed_pii"] == 0
    assert result.iloc[1]["miss_rate_percent"] == 0.0
def test_linkage_attack():
    import pandas as pd
    from pii_pipeline.reidentify import linkage_attack

    pseudo = pd.DataFrame([
        {"token": "P001", "city": "Bengaluru", "age": 27, "job": "Architect"},
        {"token": "P002", "city": "Mysuru", "age": 35, "job": "Teacher"},
        {"token": "P003", "city": "Bengaluru", "age": 27, "job": "Engineer"},
    ])

    auxiliary = pd.DataFrame([
        {"name": "Alice", "city": "Bengaluru", "age": 27, "job": "Architect"},
        {"name": "Bob", "city": "Mysuru", "age": 35, "job": "Teacher"},
        {"name": "Charlie", "city": "Bengaluru", "age": 27, "job": "Engineer"},
        {"name": "David", "city": "Bengaluru", "age": 27, "job": "Engineer"},
    ])

    unique, total, rate = linkage_attack(
        pseudo, auxiliary, ["city", "age", "job"]
    )

    assert unique == 2
    assert total == 3
    assert round(rate, 1) == 66.7