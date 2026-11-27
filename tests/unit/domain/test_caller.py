from app.domain.caller import CaseworkerCaller, ProviderCaller


def test_provider_can_access_resource_owned_by_one_of_its_offices():
    caller = ProviderCaller(office_codes=frozenset({"0U651L", "1A234B"}))

    assert caller.can_access_resource_owned_by("1A234B") is True


def test_provider_cannot_access_resource_owned_by_another_office():
    caller = ProviderCaller(office_codes=frozenset({"0U651L"}))

    assert caller.can_access_resource_owned_by("1A234B") is False


def test_provider_without_office_codes_cannot_access_any_resource():
    caller = ProviderCaller(office_codes=frozenset())

    assert caller.can_access_resource_owned_by("0U651L") is False


def test_caseworker_can_access_resource_owned_by_any_office():
    assert CaseworkerCaller().can_access_resource_owned_by("1A234B") is True
