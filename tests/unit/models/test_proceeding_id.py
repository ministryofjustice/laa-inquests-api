from app.models.application.enums import ProceedingId


def test_proceeding_id_contains_exactly_iq011_to_iq042():
    expected = [f"IQ{n:03d}" for n in range(11, 43)]

    assert [member.value for member in ProceedingId] == expected
