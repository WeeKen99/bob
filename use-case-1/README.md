# Use Case 1: Golden Customer Record

## Problem Statement

A bank's customer data is fragmented across **core banking**, **credit card**, and **mortgage** systems — each with different field names, ID formats, and record structures. This causes:

- Duplicate customer outreach
- KYC/AML compliance false positives and negatives
- Inaccurate risk aggregation across products

## Solution

A canonical **Golden Customer** data model and ETL pipeline that:

1. **Ingests** three mock source CSVs (20 rows each) with deliberate duplicates and format mismatches
2. **Normalises** all field names, date formats, phone numbers, gender codes, and country values
3. **Matches & deduplicates** records using a priority-based strategy
4. **Loads** results into a unified golden schema CSV

## Project Structure

```
use-case-1/
├── data/
│   ├── source/
│   │   ├── core_banking.csv      # Source system 1 — cust_id, dob YYYY-MM-DD
│   │   ├── credit_card.csv       # Source system 2 — card_id, dob DD/MM/YYYY
│   │   └── mortgage.csv          # Source system 3 — mortgage_ref, no gender field
│   └── output/
│       ├── golden_customers.csv  # Generated: unified golden records
│       └── duplicate_log.csv     # Generated: audit trail of merged duplicates
├── schema/
│   └── golden_customer.schema.json   # JSON Schema for the canonical model
├── etl/
│   └── golden_etl.py            # ETL pipeline (pure Python stdlib + difflib)
└── tests/
    └── test_golden_etl.py        # 34 unit tests (pytest)
```

## Match Strategy

Records are deduplicated using the following priority order:

| Priority | Method | Confidence |
|----------|--------|------------|
| 1 | **Exact email match** | 1.00 |
| 2 | **Fuzzy name + exact DOB** (similarity ≥ 0.80) | 0.80–1.00 |
| 3 | No match → new golden record | — |

### Deliberate Duplicates Baked In

| Duplicate | Description |
|-----------|-------------|
| `CB001` / `CB011` / `CC-10045` / `CC-10059` / `MG-2001` / `MG-2011` | John Smith — different name spellings (Jon Smyth, J., Johnathan), two emails |
| `CB003` / `CC-10062` | Robert Johnson — same email, different source IDs |

## Golden Customer Schema

See [`schema/golden_customer.schema.json`](schema/golden_customer.schema.json) for the full JSON Schema definition.

Key fields:

| Field | Description |
|-------|-------------|
| `golden_id` | Surrogate key (GC-00001, GC-00002, ...) |
| `first_name` / `last_name` | Canonical name (title-cased) |
| `dob` | ISO 8601 date (YYYY-MM-DD) |
| `email` | Lowercased primary email |
| `source_ids` | Original IDs from each source system |
| `products` | Flags: `has_core_banking`, `has_credit_card`, `has_mortgage` |
| `match_method` | How the record was consolidated |
| `confidence_score` | Match confidence (1.0 = exact) |
| `is_duplicate_flag` | True if merged from multiple sources |

## Running the ETL

**Requirements:** Python 3.10+ (no external dependencies)

```bash
cd use-case-1
python etl/golden_etl.py
```

Expected output:
```
Golden Customer ETL Pipeline
[1/4] Ingesting source data...   60 records total
[2/4] Matching and deduplicating... 20 golden records, 40 duplicates merged
[3/4] Writing golden_customers.csv...
[4/4] Writing duplicate_log.csv...
[OK] ETL complete.
```

## Running Tests

```bash
cd use-case-1
pip install pytest
python -m pytest tests/test_golden_etl.py -v
```

**34 tests** covering normalisation, matching, fuzzy logic, and merge behaviour.

## Why It Matters

Master data management projects like this typically take **weeks of manual mapping and reconciliation**. This pipeline demonstrates how much of that engineering can be auto-generated:

- Reduces duplicate-customer noise in KYC screening
- Cuts manual reconciliation effort
- Improves accuracy of cross-product risk views
- Produces a reusable consolidation pipeline blueprint for data engineering teams
