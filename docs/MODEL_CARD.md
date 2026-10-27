# Model / Data Card
## Pipeline purpose
Detect and pseudonymize names, phone numbers and emails in customer-support text.
## Components
Presidio AnalyzerEngine (spaCy en_core_web_lg + regex recognizers); HMAC-SHA256 keyed pseudonyms.
## Data
ai4privacy/pii-masking-200k (synthetic, labeled); Bitext customer-support (public). No real personal data.
## Metrics
(fill: precision / recall / F1 per entity, throughput, re-identification success rate)
## Limitations & risks
(fill: missed PII, non-English text, quasi-identifiers, key management)
## Ethics statement
(fill)
