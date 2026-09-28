"""
Golden Customer ETL Pipeline
==============================
Ingests three mock source CSVs (core banking, credit card, mortgage),
normalises field names, matches & deduplicates records, and outputs a
unified Golden Customer CSV.

Match strategy (in priority order):
  1. Exact email match
  2. Fuzzy name + exact DOB  (Levenshtein similarity >= 0.80)
  3. Records that don't match any existing golden record → new golden entry

Usage:
    python etl/golden_etl.py

Output:
    data/output/golden_customers.csv
    data/output/duplicate_log.csv
"""

import csv
import json
import os
import re
import uuid
from datetime import datetime, date
from difflib import SequenceMatcher
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent.parent
SOURCE_DIR = BASE_DIR / "data" / "source"
OUTPUT_DIR = BASE_DIR / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CORE_BANKING_FILE = SOURCE_DIR / "core_banking.csv"
CREDIT_CARD_FILE  = SOURCE_DIR / "credit_card.csv"
MORTGAGE_FILE     = SOURCE_DIR / "mortgage.csv"

GOLDEN_OUTPUT     = OUTPUT_DIR / "golden_customers.csv"
DUPLICATE_LOG     = OUTPUT_DIR / "duplicate_log.csv"

FUZZY_THRESHOLD   = 0.80   # minimum name similarity to consider a match

# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def normalise_date(raw: str) -> str | None:
    """Parse various date formats and return ISO YYYY-MM-DD or None."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalise_gender(raw: str) -> str | None:
    mapping = {"m": "M", "male": "M", "f": "F", "female": "F"}
    return mapping.get(raw.strip().lower()) if raw else None


def normalise_phone(raw: str) -> str | None:
    """Strip all non-digit characters."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits if digits else None


def normalise_email(raw: str) -> str | None:
    return raw.strip().lower() if raw and raw.strip() else None


def normalise_name(raw: str) -> str:
    return raw.strip().title() if raw else ""


def normalise_country(raw: str) -> str | None:
    mapping = {
        "usa": "USA", "united states": "USA",
        "united states of america": "USA",
    }
    return mapping.get(raw.strip().lower(), raw.strip().upper()) if raw else None


# ---------------------------------------------------------------------------
# Ingest functions — each returns a list of normalised dicts
# ---------------------------------------------------------------------------

def ingest_core_banking() -> list[dict]:
    records = []
    with open(CORE_BANKING_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append({
                "source":            "core_banking",
                "source_id":         row["cust_id"].strip(),
                "first_name":        normalise_name(row["first_name"]),
                "last_name":         normalise_name(row["last_name"]),
                "dob":               normalise_date(row["dob"]),
                "gender":            normalise_gender(row["gender"]),
                "email":             normalise_email(row["email"]),
                "phone":             normalise_phone(row["phone"]),
                "address":           row["address"].strip(),
                "city":              row["city"].strip(),
                "state":             row["state"].strip().upper(),
                "zip":               row["zip"].strip(),
                "country":           normalise_country(row["country"]),
            })
    return records


def ingest_credit_card() -> list[dict]:
    records = []
    with open(CREDIT_CARD_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append({
                "source":            "credit_card",
                "source_id":         row["card_id"].strip(),
                "first_name":        normalise_name(row["account_holder_first"]),
                "last_name":         normalise_name(row["account_holder_last"]),
                "dob":               normalise_date(row["date_of_birth"]),
                "gender":            normalise_gender(row["sex"]),
                "email":             normalise_email(row["contact_email"]),
                "phone":             normalise_phone(row["mobile"]),
                "address":           row["street"].strip(),
                "city":              row["city"].strip(),
                "state":             row["province"].strip().upper(),
                "zip":               row["postal_code"].strip(),
                "country":           normalise_country(row["nation"]),
            })
    return records


def ingest_mortgage() -> list[dict]:
    records = []
    with open(MORTGAGE_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append({
                "source":            "mortgage",
                "source_id":         row["mortgage_ref"].strip(),
                "first_name":        normalise_name(row["borrower_fname"]),
                "last_name":         normalise_name(row["borrower_lname"]),
                "dob":               normalise_date(row["birth_date"]),
                "gender":            None,
                "email":             normalise_email(row["borrower_email"]),
                "phone":             normalise_phone(row["borrower_phone"]),
                "address":           row["property_address"].strip(),
                "city":              row["property_city"].strip(),
                "state":             row["property_state"].strip().upper(),
                "zip":               row["property_zip"].strip(),
                "country":           "USA",
            })
    return records


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def full_name_similarity(rec_a: dict, rec_b: dict) -> float:
    first_sim = name_similarity(rec_a["first_name"], rec_b["first_name"])
    last_sim  = name_similarity(rec_a["last_name"],  rec_b["last_name"])
    return (first_sim + last_sim) / 2


def match_record(incoming: dict, golden_records: list[dict]) -> tuple[dict | None, str, float]:
    """
    Try to find an existing golden record that matches `incoming`.
    Returns (matched_golden_record | None, match_method, confidence_score).
    """
    # 1. Exact email match
    if incoming["email"]:
        for g in golden_records:
            if g["email"] and g["email"] == incoming["email"]:
                return g, "email_match", 1.0

    # 2. Fuzzy name + exact DOB
    if incoming["dob"]:
        for g in golden_records:
            if g["dob"] == incoming["dob"]:
                sim = full_name_similarity(incoming, g)
                if sim >= FUZZY_THRESHOLD:
                    return g, "fuzzy_name_dob", round(sim, 4)

    return None, "", 0.0


# ---------------------------------------------------------------------------
# Golden record builder
# ---------------------------------------------------------------------------

_golden_counter = 0

def new_golden_id() -> str:
    global _golden_counter
    _golden_counter += 1
    return f"GC-{_golden_counter:05d}"


def make_golden_record(record: dict, method: str, confidence: float) -> dict:
    now = datetime.utcnow().isoformat() + "Z"
    source_ids = {"core_banking_id": None, "credit_card_id": None, "mortgage_id": None}
    source_ids[f"{record['source']}_id"] = record["source_id"]
    products = {
        "has_core_banking": record["source"] == "core_banking",
        "has_credit_card":  record["source"] == "credit_card",
        "has_mortgage":     record["source"] == "mortgage",
    }
    return {
        "golden_id":        new_golden_id(),
        "first_name":       record["first_name"],
        "last_name":        record["last_name"],
        "dob":              record["dob"],
        "gender":           record["gender"],
        "email":            record["email"],
        "phone":            record["phone"],
        "address":          record["address"],
        "city":             record["city"],
        "state":            record["state"],
        "zip":              record["zip"],
        "country":          record["country"],
        "source_ids":       source_ids,
        "products":         products,
        "match_method":     method or "email_match",
        "confidence_score": confidence,
        "is_duplicate_flag": False,
        "created_at":       now,
        "updated_at":       now,
    }


def merge_into_golden(golden: dict, incoming: dict, method: str, confidence: float) -> None:
    """Update an existing golden record with info from a new source."""
    now = datetime.utcnow().isoformat() + "Z"
    source_key = f"{incoming['source']}_id"
    golden["source_ids"][source_key] = incoming["source_id"]
    golden["products"][f"has_{incoming['source']}"] = True

    # Fill in any missing fields from the incoming record
    for field in ("gender", "phone", "address", "city", "state", "zip", "country"):
        if not golden.get(field) and incoming.get(field):
            golden[field] = incoming[field]

    golden["is_duplicate_flag"] = True
    golden["updated_at"]        = now
    golden["match_method"]      = method
    golden["confidence_score"]  = min(golden["confidence_score"], confidence)


# ---------------------------------------------------------------------------
# Main ETL pipeline
# ---------------------------------------------------------------------------

def run_etl():
    print("=" * 60)
    print("Golden Customer ETL Pipeline")
    print("=" * 60)

    # 1. Ingest
    print("\n[1/4] Ingesting source data...")
    cb_records = ingest_core_banking()
    cc_records = ingest_credit_card()
    mg_records = ingest_mortgage()
    all_records = cb_records + cc_records + mg_records
    print(f"      Core Banking : {len(cb_records)} records")
    print(f"      Credit Card  : {len(cc_records)} records")
    print(f"      Mortgage     : {len(mg_records)} records")
    print(f"      Total        : {len(all_records)} records")

    # 2. Match & Dedupe
    print("\n[2/4] Matching and deduplicating...")
    golden_records: list[dict] = []
    duplicate_log:  list[dict] = []

    for record in all_records:
        matched, method, confidence = match_record(record, golden_records)

        if matched:
            duplicate_log.append({
                "incoming_source":    record["source"],
                "incoming_source_id": record["source_id"],
                "matched_golden_id":  matched["golden_id"],
                "match_method":       method,
                "confidence_score":   confidence,
            })
            merge_into_golden(matched, record, method, confidence)
        else:
            golden_records.append(make_golden_record(record, "email_match", 1.0))

    print(f"      Golden records created : {len(golden_records)}")
    print(f"      Duplicates merged      : {len(duplicate_log)}")

    # 3. Write golden output
    print("\n[3/4] Writing golden_customers.csv...")
    golden_fields = [
        "golden_id", "first_name", "last_name", "dob", "gender",
        "email", "phone", "address", "city", "state", "zip", "country",
        "cb_id", "cc_id", "mg_id",
        "has_core_banking", "has_credit_card", "has_mortgage",
        "match_method", "confidence_score", "is_duplicate_flag",
        "created_at", "updated_at",
    ]
    with open(GOLDEN_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=golden_fields)
        writer.writeheader()
        for g in golden_records:
            writer.writerow({
                "golden_id":         g["golden_id"],
                "first_name":        g["first_name"],
                "last_name":         g["last_name"],
                "dob":               g["dob"],
                "gender":            g["gender"] or "",
                "email":             g["email"] or "",
                "phone":             g["phone"] or "",
                "address":           g["address"] or "",
                "city":              g["city"] or "",
                "state":             g["state"] or "",
                "zip":               g["zip"] or "",
                "country":           g["country"] or "",
                "cb_id":             g["source_ids"].get("core_banking_id") or "",
                "cc_id":             g["source_ids"].get("credit_card_id") or "",
                "mg_id":             g["source_ids"].get("mortgage_id") or "",
                "has_core_banking":  g["products"]["has_core_banking"],
                "has_credit_card":   g["products"]["has_credit_card"],
                "has_mortgage":      g["products"]["has_mortgage"],
                "match_method":      g["match_method"],
                "confidence_score":  g["confidence_score"],
                "is_duplicate_flag": g["is_duplicate_flag"],
                "created_at":        g["created_at"],
                "updated_at":        g["updated_at"],
            })
    print(f"      Saved -> {GOLDEN_OUTPUT}")

    # 4. Write duplicate log
    print("\n[4/4] Writing duplicate_log.csv...")
    with open(DUPLICATE_LOG, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "incoming_source", "incoming_source_id",
            "matched_golden_id", "match_method", "confidence_score"
        ])
        writer.writeheader()
        writer.writerows(duplicate_log)
    print(f"      Saved -> {DUPLICATE_LOG}")

    print("\n[OK] ETL complete.\n")
    return golden_records, duplicate_log


if __name__ == "__main__":
    run_etl()
