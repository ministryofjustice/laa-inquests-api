import logging

from app.logging_utils import log_level_from_name, mask_recipient


# COPILOT TODO: This should be removed, we never want to do that
def test_log_level_from_name_uses_environment_defaults_when_unset():
    assert log_level_from_name(None, "local") == logging.DEBUG
    assert log_level_from_name(None, "dev") == logging.INFO
    assert log_level_from_name(None, "staging") == logging.INFO
    assert log_level_from_name(None, "prod") == logging.WARNING


def test_log_level_from_name_falls_back_to_info_for_invalid_value():
    assert log_level_from_name("banana", "prod") == logging.INFO


def test_mask_recipient_masks_email_local_part():
    assert mask_recipient("provider@example.com") == "p***@example.com"


def test_mask_recipient_returns_redacted_for_non_email_values():
    assert mask_recipient("+447700900123") == "***"
