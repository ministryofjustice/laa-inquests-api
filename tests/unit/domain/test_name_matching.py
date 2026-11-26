import pytest

from app.domain.name_matching import name_match_key


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("José García", "Jose Garcia"),
        ("Jos\u00e9", "Jose\u0301"),
        ("ÉMILE", "emile"),
        ("Siân", "Sian"),
        ("Gŵyn", "Gwyn"),
        ("Nguyễn", "Nguyen"),
        ("İbrahim", "Ibrahim"),
        ("Łukasz", "Lukasz"),
        ("Ørsted", "Orsted"),
        ("Đorđe", "Dorde"),
        ("Æsop", "Aesop"),
        ("Straße", "Strasse"),
        ("ＪＡＮＥ", "Jane"),
    ],
)
def test_names_that_differ_only_in_accents_case_or_letter_form_match(first, second):
    assert name_match_key(first) == name_match_key(second)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("O'Brien", "O\u2019Brien"),
        ("O'Brien", "OBrien"),
        ("Mary-Jane", "Mary Jane"),
        ("Mary\u2010Jane", "Mary-Jane"),
        ("  Mary   Jane  ", "Mary Jane"),
        ("Jane\u00a0Smith", "Jane Smith"),
    ],
)
def test_apostrophes_hyphens_and_runs_of_whitespace_do_not_stop_a_match(first, second):
    assert name_match_key(first) == name_match_key(second)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Smith", "Smyth"),
        ("Jon", "John"),
        ("Anna", "Hanna"),
        ("Mary Jane", "Maryjane"),
        ("Müller", "Mueller"),
        ("Jane Smith", "Smith Jane"),
    ],
)
def test_different_names_do_not_match(first, second):
    assert name_match_key(first) != name_match_key(second)


def test_the_key_is_lower_case_ascii_for_common_latin_names():
    assert name_match_key("José García") == "jose garcia"


@pytest.mark.parametrize("value", ["José García", "O'Brien", "Straße", "  Mary-Jane "])
def test_the_key_is_stable_when_applied_again(value):
    assert name_match_key(name_match_key(value)) == name_match_key(value)


@pytest.mark.parametrize("value", ["", " ", "\n\t"])
def test_blank_names_have_an_empty_key(value):
    assert name_match_key(value) == ""
