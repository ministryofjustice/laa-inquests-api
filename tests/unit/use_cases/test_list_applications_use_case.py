from unittest.mock import MagicMock

from app.models.application.index import Application
from app.ports.list_applications_port import ListApplicationsPort
from app.use_cases.list_applications import ListApplicationsUseCase


def test_execute_returns_applications_from_list_applications_port():
    applications = [
        Application(laa_reference=1, deceased_id=1, provider_id=1),
        Application(laa_reference=2, deceased_id=2, provider_id=2),
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
