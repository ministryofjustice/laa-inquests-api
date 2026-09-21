import base64

from app.domain.reference_rules import AMBIGUOUS_CHARACTERS, ReferenceRules


def test_allowed_characters_exclude_ambiguous_characters():
    rules = ReferenceRules(banned_words=[])

    assert all(char not in rules.allowed_characters for char in AMBIGUOUS_CHARACTERS)
    assert "A" in rules.allowed_characters
    assert "7" in rules.allowed_characters


def test_contains_banned_word_detects_configured_word():
    rules = ReferenceRules(banned_words=["FAKE"])

    assert rules.contains_banned_word("XXFAKEXX") is True
    assert rules.contains_banned_word("XXXXYYYY") is False


def test_banned_words_containing_ambiguous_characters_are_ignored():
    # A word that can never be generated (contains ambiguous chars) is filtered out.
    rules = ReferenceRules(banned_words=["B8G6"])

    assert rules.banned_words == []
    assert rules.contains_banned_word("B8G6") is False


def test_from_file_decodes_base64_banned_words(tmp_path):
    banned_file = tmp_path / "banned-words.txt"
    encoded = base64.b64encode(b"FAKE").decode("utf-8")
    banned_file.write_text(f"{encoded}\n")

    rules = ReferenceRules.from_file(str(banned_file))

    assert rules.contains_banned_word("AAFAKEAA") is True
