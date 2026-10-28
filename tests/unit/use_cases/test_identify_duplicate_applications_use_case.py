from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError

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


def test_identify_duplicate_applications_reraises_exception_from_port_when_identify_duplicates_fails():
    duplicate_applications_port = MagicMock(spec=DuplicateApplicationsPort)
    application_id = 1
    exception = LookupError(f"Application with id {application_id} does not exist")
    duplicate_applications_port.identify_duplicates.side_effect = exception

    identify_duplicate_applications_use_case = IdentifyDuplicateApplicationsUseCase(
        duplicate_applications_port=duplicate_applications_port
    )

    try:
        identify_duplicate_applications_use_case.execute(application_id=application_id)
    except LookupError as e:
        assert e == exception
    else:
        assert False, "Exception was not raised"


def test_identify_duplicate_applications_creates_duplicate_records():
    duplicate_applications_port = MagicMock(spec=DuplicateApplicationsPort)
    application_id = 1
    duplicate_application_ids = [2, 3]
    duplicate_applications_port.identify_duplicates.return_value = (
        duplicate_application_ids
    )

    identify_duplicate_applications_use_case = IdentifyDuplicateApplicationsUseCase(
        duplicate_applications_port=duplicate_applications_port
    )

    identify_duplicate_applications_use_case.execute(application_id=application_id)

    duplicate_applications_port.create_duplicate_records.assert_called_once_with(
        application_id, duplicate_application_ids
    )


def test_identify_duplicagte_applications_deos_not_create_duplicate_records_when_no_duplicates():
    duplicate_applications_port = MagicMock(spec=DuplicateApplicationsPort)
    application_id = 1
    duplicate_applications_port.identify_duplicates.return_value = []

    identify_duplicate_applications_use_case = IdentifyDuplicateApplicationsUseCase(
        duplicate_applications_port=duplicate_applications_port
    )

    identify_duplicate_applications_use_case.execute(application_id=application_id)

    duplicate_applications_port.create_duplicate_records.assert_not_called()


def test_identify_duplicate_applications_reraises_exception_from_port_when_create_duplicate_records_fails():
    duplicate_applications_port = MagicMock(spec=DuplicateApplicationsPort)
    application_id = 1
    exception = IntegrityError(
        f"Failed to create duplicate records for application with id {application_id}",
        None,
        None,
    )
    duplicate_applications_port.identify_duplicates.return_value = [2, 3]
    duplicate_applications_port.create_duplicate_records.side_effect = exception

    identify_duplicate_applications_use_case = IdentifyDuplicateApplicationsUseCase(
        duplicate_applications_port=duplicate_applications_port
    )

    try:
        identify_duplicate_applications_use_case.execute(application_id=application_id)
    except IntegrityError as e:
        assert e == exception
    else:
        assert False, "Exception was not raised"
