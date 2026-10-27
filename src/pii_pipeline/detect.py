"""Shared Presidio detection, with an unchanged baseline and optional tuned rules."""
import re
from functools import lru_cache

ENTITIES = ("PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS")
# Conservative pattern for the 2-6-6-1 IMEI formatting seen in the dataset.
IMEI_FORMAT = re.compile(r"(?<![\w\d])\d{2}-\d{6}-\d{6}-\d(?![\w\d])")
IPV4_FORMAT = re.compile(r"(?<![\w\d])(?:\d{1,3}\.){3}\d{1,3}(?![\w\d])")


def _ip_spans(text):
    spans = []
    for m in IPV4_FORMAT.finditer(text):
        if all(0 <= int(x) <= 255 for x in m.group().split(".")):
            spans.append((m.start(), m.end()))
    return spans


def _overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


@lru_cache(maxsize=2)
def get_analyzer(mode="baseline"):
    if mode not in ("baseline", "tuned"):
        raise ValueError("mode must be baseline or tuned")
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer import Pattern, PatternRecognizer
    analyzer = AnalyzerEngine()
    if mode == "tuned":
        recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            name="DatasetIMEIFormatRecognizer",
            patterns=[Pattern(name="imei_2_6_6_1", regex=IMEI_FORMAT.pattern, score=0.65)],
        )
        analyzer.registry.add_recognizer(recognizer)
    return analyzer


def detect(text, mode="baseline"):
    """Return Presidio RecognizerResult objects; suppress IPv4-as-phone only when tuned."""
    if not isinstance(text, str) or not text:
        return []
    results = get_analyzer(mode).analyze(text=text, language="en", entities=list(ENTITIES))
    if mode == "tuned":
        ips = _ip_spans(text)
        results = [r for r in results if not (
            r.entity_type == "PHONE_NUMBER" and
            any(_overlap((r.start, r.end), ip) for ip in ips)
        )]
    return results


def resolve_overlaps(results):
    """Select non-overlapping results, favoring higher confidence then longer spans."""
    selected = []
    for r in sorted(results, key=lambda r: (-r.score, -(r.end-r.start), r.start)):
        if not any(_overlap((r.start, r.end), (x.start, x.end)) for x in selected):
            selected.append(r)
    return sorted(selected, key=lambda r: r.start, reverse=True)
