from tests.unit.factories import create_base_claim


def test_claim_keeps_internal_application_id():
    claim = create_base_claim(application_id=12345)

    assert claim.application_id == 12345
