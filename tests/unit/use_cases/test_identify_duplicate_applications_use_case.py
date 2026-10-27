from unittest.mock import MagicMock

from app.ports.duplicate_applications_port import DuplicateApplicationsPort
from app.use_cases.identify_duplicate_applications import (
    IdentifyDuplicateApplicationsUseCase,
)


def test_identify_duplicate_applications_calls_port_with_application_id():
    duplicate_applications_port = MagicMock(spec=DuplicateApplicationsPort)
    application_id = 1

    identify_duplicate_applications_use_case = IdentifyDuplicateApplicationsUseCase(
        duplicate_applications_port=duplicate_applications_port
    )

    identify_duplicate_applications_use_case.execute(application_id=application_id)

    duplicate_applications_port.identify_duplicates.assert_called_once_with(
        application_id
    )


def test_identify_duplicate_applications_reraises_exception_from_port():
    duplicate_applications_port = MagicMock(spec=DuplicateApplicationsPort)
    application_id = 1
    exception = LookupError(f"Application with id {application_id} does not exist")
    duplicate_applications_port.identify_duplicates.side_effect = exception

    identify_duplicate_applications_use_case = IdentifyDuplicateApplicationsUseCase(
        duplicate_applications_port=duplicate_applications_port
    )

    try:
        identify_duplicate_applications_use_case.execute(application_id=application_id)
    except Exception as e:
        assert e == exception
    else:
        assert False, "Exception was not raised"
