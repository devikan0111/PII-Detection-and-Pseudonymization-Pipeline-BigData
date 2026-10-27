from pii_pipeline.spark_job import token

def test_deterministic():
    assert token("PERSON", "Alice") == token("PERSON", "Alice")

def test_differs():
    assert token("PERSON", "Alice") != token("PERSON", "Bob")
