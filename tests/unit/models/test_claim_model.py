from tests.unit.factories import create_base_claim


def test_claim_laa_reference_returns_string_of_application_id():
    claim = create_base_claim(application_id=12345)

    assert claim.laa_reference == "12345"
