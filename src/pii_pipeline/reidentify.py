"""Re-identification risk experiments using synthetic PII."""

import hashlib
import hmac


def make_token(entity_type, value, secret):
    """Generate an HMAC pseudonym using the supplied key."""
    message = f"{entity_type}:{value}".encode()
    digest = hmac.new(secret, message, hashlib.sha256).hexdigest()[:10]
    return f"<{entity_type}_{digest}>"


def dictionary_attack(target_token, entity_type, candidates, attacker_key):
    """Try to identify the original value using candidate guesses."""
    return [
        value
        for value in candidates
        if make_token(entity_type, value, attacker_key) == target_token
    ]



def evaluate_dictionary_attack(originals, candidates, correct_key, attacker_key):
    """Measure the percentage of original values identified."""
    successes = 0

    for original in originals:
        target = make_token("EMAIL_ADDRESS", original, correct_key)

        matches = dictionary_attack(
            target, "EMAIL_ADDRESS", candidates, attacker_key
        )

        if original in matches:
            successes += 1

    return successes, 100 * successes / len(originals) if originals else 0.0

def missed_pii_analysis(metrics):
    """Calculate missed PII counts using one-to-one evaluation."""
    rows = metrics[metrics["mode"] == "one_to_one"].copy()

    rows["missed_pii"] = rows["gold"] - rows["found_gold"]
    rows["miss_rate_percent"] = (
        100 * rows["missed_pii"] / rows["gold"]
    ).round(2)

    return rows[
        ["entity", "gold", "found_gold",
         "missed_pii", "miss_rate_percent"]
    ]

def linkage_attack(pseudo, auxiliary, quasi_identifiers):
    """Measure unique identity matches using quasi-identifiers."""

    matches = pseudo.merge(
        auxiliary,
        on=quasi_identifiers,
        how="left",
        indicator=True
    )

    # Count how many auxiliary identities match each combination.
    match_counts = (
        auxiliary.groupby(quasi_identifiers)
        .size()
        .reset_index(name="candidate_count")
    )

    matches = matches.merge(
        match_counts,
        on=quasi_identifiers,
        how="left"
    )

    # Only one matching auxiliary identity means a unique match.
    uniquely_matched = (
        (matches["_merge"] == "both") &
        (matches["candidate_count"] == 1)
    )

    unique_tokens = matches.loc[uniquely_matched, "token"].nunique()
    total = len(pseudo)

    rate = 100 * unique_tokens / total if total else 0.0

    return unique_tokens, total, rate

def main():
    original = "alice@example.com"
    correct_key = b"experiment-only-secret"
    wrong_key = b"attacker-wrong-secret"

    candidates = [
        "bob@example.com",
        "charlie@example.com",
        "alice@example.com",
        "david@example.com",
    ]

    target = make_token("EMAIL_ADDRESS", original, correct_key)

    correct_matches = dictionary_attack(
        target, "EMAIL_ADDRESS", candidates, correct_key
    )

    wrong_matches = dictionary_attack(
        target, "EMAIL_ADDRESS", candidates, wrong_key
    )

    print("Target token:", target)
    print("Correct-key matches:", correct_matches)
    print("Wrong-key matches:", wrong_matches)
    print("Correct-key attack successful:", original in correct_matches)
    print("Wrong-key attack successful:", original in wrong_matches)


if __name__ == "__main__":
    main()