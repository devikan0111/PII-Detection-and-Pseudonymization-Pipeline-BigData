from types import SimpleNamespace
from pii_pipeline.detect import IMEI_FORMAT, _ip_spans, resolve_overlaps, detect


def test_imei_format():
    assert IMEI_FORMAT.findall("IMEI 40-125891-098657-8.") == ["40-125891-098657-8"]
    assert not IMEI_FORMAT.findall("reference 123-125891-098657-8")


def test_ipv4_validation():
    assert _ip_spans("139.26.117.172 and 999.26.117.172") == [(0, 14)]


def test_overlapping_results_prefer_confidence():
    low = SimpleNamespace(start=0, end=10, score=0.3)
    high = SimpleNamespace(start=3, end=8, score=0.9)
    assert resolve_overlaps([low, high]) == [high]


def test_tuned_filters_ip_phone_predictions(monkeypatch):
    import pii_pipeline.detect as module
    class FakeAnalyzer:
        def analyze(self, **kwargs):
            return [SimpleNamespace(start=0, end=14, entity_type="PHONE_NUMBER", score=0.7)]
    monkeypatch.setattr(module, "get_analyzer", lambda mode: FakeAnalyzer())
    assert detect("139.26.117.172", mode="tuned") == []
    assert len(detect("139.26.117.172", mode="baseline")) == 1
