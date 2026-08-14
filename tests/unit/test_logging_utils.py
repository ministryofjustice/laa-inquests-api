import logging

from app.logging_utils import log_level_from_name, mask_recipient


def test_log_level_from_name_falls_back_to_info_when_unset():
    assert log_level_from_name(None) == logging.INFO
    assert log_level_from_name("") == logging.INFO


def test_log_level_from_name_falls_back_to_info_for_invalid_value():
    assert log_level_from_name("banana") == logging.INFO


def test_log_level_from_name_accepts_valid_values():
    assert log_level_from_name("debug") == logging.DEBUG
    assert log_level_from_name("warn") == logging.WARNING
    assert log_level_from_name("fatal") == logging.CRITICAL


def test_mask_recipient_masks_email_local_part():
    assert mask_recipient("provider@example.com") == "p***@example.com"


def test_mask_recipient_returns_redacted_for_non_email_values():
    assert mask_recipient("+447700900123") == "***"
