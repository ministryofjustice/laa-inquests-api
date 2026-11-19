from app.domain.office_authorisation import is_office_authorised


def test_office_is_authorised_when_it_is_one_of_the_user_office_codes():
    assert is_office_authorised("1A234B", frozenset({"0U651L", "1A234B"})) is True


def test_office_is_not_authorised_when_it_is_not_one_of_the_user_office_codes():
    assert is_office_authorised("1A234B", frozenset({"0U651L"})) is False


def test_office_is_not_authorised_when_user_has_no_office_codes():
    assert is_office_authorised("0U651L", frozenset()) is False
