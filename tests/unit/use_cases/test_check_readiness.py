from unittest.mock import create_autospec

from app.ports.check_readiness_port import CheckReadinessPort
from app.use_cases.check_readiness import CheckReadinessUseCase


def test_check_readiness_checks_required_dependencies() -> None:
    readiness_port = create_autospec(CheckReadinessPort, instance=True)
    use_case = CheckReadinessUseCase(readiness_port)

    use_case.execute()

    readiness_port.check.assert_called_once_with()
