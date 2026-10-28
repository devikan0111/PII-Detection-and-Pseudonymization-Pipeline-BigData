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