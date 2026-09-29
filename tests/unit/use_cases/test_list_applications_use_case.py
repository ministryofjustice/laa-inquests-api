from unittest.mock import MagicMock

from app.ports.list_applications_port import ListApplicationsPort
from app.use_cases.list_applications import ListApplicationsUseCase
from tests.factories.builders import build_application


def test_execute_returns_applications_from_list_applications_port():
    applications = [
        build_application(application_id=1),
        build_application(application_id=2, laa_reference="INQ-ZZZ-ZZZ"),
    ]
    list_applications_port = MagicMock(spec=ListApplicationsPort)
    list_applications_port.list_applications.return_value = applications

    use_case = ListApplicationsUseCase(list_applications_port=list_applications_port)

    result = use_case.execute()

    assert result == applications
    list_applications_port.list_applications.assert_called_once_with()


def test_execute_returns_empty_list_when_no_applications_exist():
    list_applications_port = MagicMock(spec=ListApplicationsPort)
    list_applications_port.list_applications.return_value = []

    use_case = ListApplicationsUseCase(list_applications_port=list_applications_port)

    result = use_case.execute()

    assert result == []
    list_applications_port.list_applications.assert_called_once_with()
