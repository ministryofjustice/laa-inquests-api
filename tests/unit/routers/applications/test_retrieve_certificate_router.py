import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

from app.models.application.certificate import (
    ApplicationCertificateResponse,
)
from app.routers.applications import read_certificate
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ApplicationNotGrantedError,
    ProceedingsNotFoundError,
    ProviderDetailsRetrievalError,
)
from tests.unit.factories import create_base_certificate


def test_read_certificate_calls_use_case_with_laa_reference():
    use_case = MagicMock()
    use_case.execute.return_value = create_base_certificate()

    read_certificate("123", use_case=use_case)

    use_case.execute.assert_called_once_with("123")


def test_read_certificate_returns_certificate_context():
    use_case = MagicMock()
    certificate_context = create_base_certificate()
    use_case.execute.return_value = certificate_context

    result = read_certificate("123", use_case=use_case)

    assert isinstance(result, ApplicationCertificateResponse)
    assert result.model_dump() == certificate_context.model_dump()


def test_read_certificate_raises_404_when_application_not_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ApplicationNotFoundError()

    with pytest.raises(HTTPException) as exception:
        read_certificate("123", use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "Application not found"


def test_read_certificate_raises_404_when_no_proceedings_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ProceedingsNotFoundError()

    with pytest.raises(HTTPException) as exception:
        read_certificate("123", use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "No proceedings found for application"


def test_read_certificate_raises_422_when_application_not_granted():
    use_case = MagicMock()
    use_case.execute.side_effect = ApplicationNotGrantedError()

    with pytest.raises(HTTPException) as exception:
        read_certificate("123", use_case=use_case)

    assert exception.value.status_code == 422
    assert exception.value.detail == "Application is not granted"


def test_read_certificate_raises_500_when_provider_details_lookup_fails():
    use_case = MagicMock()
    use_case.execute.side_effect = ProviderDetailsRetrievalError()

    with pytest.raises(HTTPException) as exception:
        read_certificate("123", use_case=use_case)

    assert exception.value.status_code == 500
    assert (
        exception.value.detail
        == "Failed to retrieve firm name from provider details service"
    )
