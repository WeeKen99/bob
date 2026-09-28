"""
Tests for Golden Customer ETL Pipeline
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'etl'))

import pytest
from golden_etl import (
    normalise_date,
    normalise_gender,
    normalise_phone,
    normalise_email,
    normalise_name,
    normalise_country,
    name_similarity,
    full_name_similarity,
    match_record,
    make_golden_record,
    merge_into_golden,
)


# ---------------------------------------------------------------------------
# Normalisation tests
# ---------------------------------------------------------------------------

class TestNormaliseDate:
    def test_iso_format(self):
        assert normalise_date("1985-03-12") == "1985-03-12"

    def test_dd_mm_yyyy(self):
        assert normalise_date("12/03/1985") == "1985-03-12"

    def test_mm_dd_yyyy(self):
        assert normalise_date("03/12/1985") == "1985-12-03"

    def test_empty_string(self):
        assert normalise_date("") is None

    def test_none_value(self):
        assert normalise_date(None) is None

    def test_invalid_format(self):
        assert normalise_date("not-a-date") is None


class TestNormaliseGender:
    def test_male_short(self):
        assert normalise_gender("M") == "M"

    def test_male_long(self):
        assert normalise_gender("Male") == "M"

    def test_female_short(self):
        assert normalise_gender("F") == "F"

    def test_female_long(self):
        assert normalise_gender("Female") == "F"

    def test_case_insensitive(self):
        assert normalise_gender("MALE") == "M"
        assert normalise_gender("female") == "F"

    def test_none(self):
        assert normalise_gender(None) is None


class TestNormalisePhone:
    def test_strips_formatting(self):
        assert normalise_phone("+1-555-0101") == "15550101"

    def test_digits_only_passthrough(self):
        assert normalise_phone("5550101") == "5550101"

    def test_none(self):
        assert normalise_phone(None) is None

    def test_empty(self):
        assert normalise_phone("") is None


class TestNormaliseEmail:
    def test_lowercase(self):
        assert normalise_email("John.Smith@Email.COM") == "john.smith@email.com"

    def test_strips_whitespace(self):
        assert normalise_email("  test@example.com  ") == "test@example.com"

    def test_none(self):
        assert normalise_email(None) is None


class TestNormaliseName:
    def test_title_case(self):
        assert normalise_name("JOHN") == "John"

    def test_strips_whitespace(self):
        assert normalise_name("  Smith  ") == "Smith"

    def test_empty_string(self):
        assert normalise_name("") == ""


class TestNormaliseCountry:
    def test_usa_variants(self):
        assert normalise_country("usa") == "USA"
        assert normalise_country("United States") == "USA"
        assert normalise_country("United States of America") == "USA"

    def test_unknown_uppercased(self):
        assert normalise_country("canada") == "CANADA"


# ---------------------------------------------------------------------------
# Matching tests
# ---------------------------------------------------------------------------

class TestNameSimilarity:
    def test_identical(self):
        assert name_similarity("John", "John") == 1.0

    def test_similar(self):
        assert name_similarity("John", "Jon") >= 0.75

    def test_different(self):
        assert name_similarity("John", "Patricia") < 0.5

    def test_abbreviation(self):
        # "J." vs "John" — should be low
        assert name_similarity("J.", "John") < 0.80


class TestMatchRecord:
    def _make_golden(self, golden_id, email, dob, first, last):
        return {
            "golden_id":        golden_id,
            "first_name":       first,
            "last_name":        last,
            "dob":              dob,
            "email":            email,
            "phone":            None,
            "source_ids":       {"core_banking_id": None, "credit_card_id": None, "mortgage_id": None},
            "products":         {"has_core_banking": True, "has_credit_card": False, "has_mortgage": False},
            "match_method":     "email_match",
            "confidence_score": 1.0,
            "is_duplicate_flag": False,
        }

    def test_exact_email_match(self):
        golden_records = [
            self._make_golden("GC-00001", "john.smith@email.com", "1985-03-12", "John", "Smith")
        ]
        incoming = {
            "source": "credit_card", "source_id": "CC-10045",
            "first_name": "John", "last_name": "Smith",
            "dob": "1985-03-12", "email": "john.smith@email.com",
        }
        match, method, confidence = match_record(incoming, golden_records)
        assert match is not None
        assert method == "email_match"
        assert confidence == 1.0

    def test_fuzzy_name_dob_match(self):
        golden_records = [
            self._make_golden("GC-00001", "john.smith@email.com", "1985-03-12", "John", "Smith")
        ]
        incoming = {
            "source": "mortgage", "source_id": "MG-2011",
            "first_name": "Johnathan", "last_name": "Smith",
            "dob": "1985-03-12", "email": "johnsmith85@gmail.com",
        }
        match, method, confidence = match_record(incoming, golden_records)
        assert match is not None
        assert method == "fuzzy_name_dob"
        assert confidence >= 0.80

    def test_no_match(self):
        golden_records = [
            self._make_golden("GC-00001", "john.smith@email.com", "1985-03-12", "John", "Smith")
        ]
        incoming = {
            "source": "credit_card", "source_id": "CC-99999",
            "first_name": "Patricia", "last_name": "Thomas",
            "dob": "1993-05-29", "email": "p.thomas@email.com",
        }
        match, method, confidence = match_record(incoming, golden_records)
        assert match is None

    def test_no_match_without_email(self):
        golden_records = [
            self._make_golden("GC-00001", None, "1985-03-12", "John", "Smith")
        ]
        incoming = {
            "source": "credit_card", "source_id": "CC-10045",
            "first_name": "John", "last_name": "Smith",
            "dob": "1985-03-12", "email": None,
        }
        match, method, confidence = match_record(incoming, golden_records)
        # Falls through to fuzzy match since email is None
        assert match is not None
        assert method == "fuzzy_name_dob"


# ---------------------------------------------------------------------------
# Merge tests
# ---------------------------------------------------------------------------

class TestMergeIntoGolden:
    def test_source_id_populated(self):
        golden = {
            "golden_id": "GC-00001", "first_name": "John", "last_name": "Smith",
            "dob": "1985-03-12", "gender": "M", "email": "john.smith@email.com",
            "phone": None, "address": None, "city": None, "state": None,
            "zip": None, "country": None,
            "source_ids": {"core_banking_id": "CB001", "credit_card_id": None, "mortgage_id": None},
            "products": {"has_core_banking": True, "has_credit_card": False, "has_mortgage": False},
            "match_method": "email_match", "confidence_score": 1.0,
            "is_duplicate_flag": False, "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z",
        }
        incoming = {
            "source": "credit_card", "source_id": "CC-10045",
            "first_name": "John", "last_name": "Smith",
            "dob": "1985-03-12", "gender": "M", "email": "john.smith@email.com",
            "phone": "5550101", "address": "12 Maple St", "city": "New York",
            "state": "NY", "zip": "10001", "country": "USA",
        }
        merge_into_golden(golden, incoming, "email_match", 1.0)

        assert golden["source_ids"]["credit_card_id"] == "CC-10045"
        assert golden["products"]["has_credit_card"] is True
        assert golden["is_duplicate_flag"] is True
        assert golden["phone"] == "5550101"

    def test_existing_fields_not_overwritten(self):
        golden = {
            "golden_id": "GC-00001", "first_name": "John", "last_name": "Smith",
            "dob": "1985-03-12", "gender": "M", "email": "john.smith@email.com",
            "phone": "EXISTING_PHONE", "address": "Existing Address", "city": "NY",
            "state": "NY", "zip": "10001", "country": "USA",
            "source_ids": {"core_banking_id": "CB001", "credit_card_id": None, "mortgage_id": None},
            "products": {"has_core_banking": True, "has_credit_card": False, "has_mortgage": False},
            "match_method": "email_match", "confidence_score": 1.0,
            "is_duplicate_flag": False, "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z",
        }
        incoming = {
            "source": "credit_card", "source_id": "CC-10045",
            "first_name": "J.", "last_name": "Smith",
            "dob": "1985-03-12", "gender": "M", "email": "john.smith@email.com",
            "phone": "NEW_PHONE", "address": "New Address", "city": "New York",
            "state": "NY", "zip": "10001", "country": "USA",
        }
        merge_into_golden(golden, incoming, "email_match", 1.0)
        # Existing phone should not be overwritten
        assert golden["phone"] == "EXISTING_PHONE"
