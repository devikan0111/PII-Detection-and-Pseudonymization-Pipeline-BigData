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