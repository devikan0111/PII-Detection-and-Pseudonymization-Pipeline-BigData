from pii_pipeline.evaluate import gold_spans, score_doc, aggregate, to_table


def test_gold_spans_maps_labels_and_skips_others():
    pm = [{"label": "FIRSTNAME", "start": 0, "end": 5, "value": "Alice"},
          {"label": "JOBAREA", "start": 10, "end": 15, "value": "x"}]
    assert gold_spans(pm) == [(0, 5, "PERSON")]


def test_overlap_counts_full_name_against_split_labels():
    gold = [(0, 5, "PERSON"), (6, 11, "PERSON")]       # first + last name labelled separately
    pred = [(0, 11, "PERSON")]                           # Presidio returns one span
    sc = score_doc(gold, pred)[("overlap", "PERSON")]
    assert sc == [1, 1, 2, 2]


def test_miss_and_false_positive():
    gold = [(0, 5, "PERSON")]
    pred = [(20, 30, "PHONE_NUMBER")]
    sc = score_doc(gold, pred)
    assert sc[("overlap", "PERSON")] == [0, 0, 1, 0]            # leaked name (recall loss)
    assert sc[("overlap", "PHONE_NUMBER")] == [1, 0, 0, 0]      # spurious (precision loss)


def test_table_precision_recall():
    gold = [(0, 5, "PERSON"), (10, 15, "PERSON")]
    pred = [(0, 5, "PERSON"), (30, 35, "PERSON")]
    t = to_table(aggregate([score_doc(gold, pred)]))
    row = t[(t["mode"] == "exact") & (t["entity"] == "PERSON")].iloc[0]
    assert row["precision"] == 0.5 and row["recall"] == 0.5


def test_one_to_one_prevents_double_counting():
    gold = [(0, 6, "PERSON"), (7, 12, "PERSON")]
    pred = [(0, 12, "PERSON")]
    scores = score_doc(gold, pred)
    assert scores[("overlap", "PERSON")] == [1, 1, 2, 2]
    assert scores[("one_to_one", "PERSON")] == [1, 1, 2, 1]
