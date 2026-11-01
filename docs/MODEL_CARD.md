# Model / Data Card

## 1. Pipeline Purpose

The PII Detection and Pseudonymization Pipeline detects and pseudonymizes personally identifiable information (PII) in customer-support text. It focuses on person names, phone numbers, and email addresses.

The goal is to reduce the exposure of sensitive information while preserving consistent pseudonyms for repeated values.

## 2. Components

- **Apache Spark:** Processes text data through a scalable data-processing pipeline.
- **Microsoft Presidio AnalyzerEngine:** Detects PII using NLP and pattern-based recognition.
- **spaCy (`en_core_web_lg`):** Supports named-entity recognition.
- **Regex recognizers:** Help identify structured information such as phone numbers and email addresses.
- **HMAC-SHA256:** Generates keyed, deterministic pseudonyms. The same input can produce the same pseudonym when the same secret key is used.
- **Parquet:** Stores structured input and processed output data.

## 3. Data

- **ai4privacy/pii-masking-200k:** A synthetic, labelled PII dataset used for PII-related processing and evaluation.
- **Bitext customer-support dataset:** Public customer-support text used in the project.

The evaluation report describes 1,000 English documents and 654 annotated PII entities. These figures should be verified against the final evaluation files.

The project uses public and synthetic datasets as documented in its data sources. Dataset contents, licensing, and provenance should be checked before reuse.

## 4. Evaluation Metrics

### Baseline vs. Tuned F1 Scores

| Entity Type | Baseline F1 | Tuned F1 |
|---|---:|---:|
| Person | 0.6776 | 0.6776 |
| Phone Number | 0.4068 | 0.7835 |
| Email Address | 1.0000 | 1.0000 |
| **Overall** | **0.6837** | **0.7344** |

The overall F1 score improved from 0.6837 to 0.7344. Phone-number detection showed the largest improvement, while person-name detection remained unchanged.

### Additional Evaluation Results

- **Missed PII entities:** 199 at baseline and 159 after tuning.
- **Throughput:** Increased from 51.56 to 57.85 rows per second in the tested configurations.
- **Dictionary experiment:** 4/5 candidate matches with the correct key and 0/5 with the wrong key.
- **Record-linkage experiment:** 2/3 unique matches.
- **Automated tests:** 15 passed.

The dictionary and record-linkage experiments used small samples and are illustrative only. They should not be interpreted as general estimates of privacy risk.

Precision and recall for each entity type should be reported using the final evaluation results.

## 5. Intended Use

The pipeline is intended for:

- Detecting names, phone numbers, and email addresses in text.
- Replacing detected PII with consistent pseudonyms.
- Evaluating PII detection performance.
- Studying residual privacy and re-identification risks.
- Experimenting with privacy-aware text-processing workflows.

The system should not be treated as a complete privacy guarantee without further validation.

## 6. Limitations and Risks

- **Missed PII:** Some sensitive information may remain undetected.
- **Language limitations:** Evaluation focused on English text; performance in other languages has not been established.
- **Context dependence:** Names and unusually formatted phone numbers can be difficult to recognize accurately.
- **Quasi-identifiers:** Information such as location, occupation, and dates may enable identification when combined with other data.
- **Key management:** The HMAC secret must remain confidential. Exposure of the key weakens the security of the pseudonymization process.
- **Limited evaluation scope:** Performance depends on the datasets, annotations, and experimental conditions.
- **Linkability:** Consistent pseudonyms can make it possible to connect records containing the same underlying value.
- **Pseudonymization is not anonymization:** Other information in a record may still identify an individual.

## 7. Privacy and Security

HMAC-SHA256 produces keyed digests; it does not encrypt the original information and cannot be used to decrypt a pseudonym.

The secret key should be stored securely and excluded from source control. Access to original data, processed data, and logs should be appropriately restricted.

The system's security depends on correct secret management and the prevention of unintended exposure of original PII.

## 8. Ethics Statement

This project aims to reduce the exposure of sensitive information in text data. It uses public and synthetic datasets as documented in its data sources.

Because PII detection is imperfect, some sensitive information may remain in processed records. The pipeline's pseudonymization mechanism also does not guarantee complete anonymity.

Responsible use requires checking dataset provenance and licensing, evaluating detection errors, protecting the secret key, restricting data access, and communicating the system's limitations.

The pipeline should not be used as the sole safeguard when preparing sensitive datasets for public release.
