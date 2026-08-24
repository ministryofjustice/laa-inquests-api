from unittest.mock import MagicMock

import pytest

from app.contexts.user import set_entra_user_context
from app.models.application.enums import PublicBodyId
from app.models.application.index import (
    Application,
)
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.update_application_public_bodies_port import ApplicationPublicBodiesPort
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.update_public_bodies import UpdatePublicBodiesUseCase
from tests.unit.factories import create_base_application


@pytest.fixture(autouse=True)
def entra_user_context() -> None:
    set_entra_user_context(None, "Caseworker")


@pytest.fixture
def application() -> Application:
    return create_base_application()


@pytest.fixture
def update_public_bodies_port(application: Application) -> MagicMock:
    port = MagicMock(spec=ApplicationPublicBodiesPort)
    port.update_public_bodies.return_value = None
    return port


@pytest.fixture
def application_lookup_port(application: Application) -> MagicMock:
    port = MagicMock(spec=ApplicationLookupPort)
    port.get_application_by_laa_reference.return_value = application
    return port


@pytest.fixture
def use_case(
    application_lookup_port: MagicMock,
    update_public_bodies_port: MagicMock,
) -> UpdatePublicBodiesUseCase:
    return UpdatePublicBodiesUseCase(
        application_lookup_port,
        update_public_bodies_port,
    )


def test_update_public_bodies_calls_application_public_bodies_port_and_commits(
    use_case,
    application,
):
    public_body_ids = [PublicBodyId.DEPARTMENT_FOR_TRANSPORT]

    use_case.execute(application.laa_reference, public_body_ids)

    use_case.update_public_bodies_port.update_public_bodies.assert_called_once_with(
        application=application,
        public_body_ids=public_body_ids,
    )
    use_case.update_public_bodies_port.commit.assert_called_once()
    use_case.update_public_bodies_port.rollback.assert_not_called()


def test_update_public_bodies_raises_exception_if_no_public_bodies_provided(
    use_case,
    application,
):
    public_body_ids = []

    use_case.update_public_bodies_port.update_public_bodies.side_effect = Exception(
        "No public bodies provided"
    )

    with pytest.raises(ValueError, match="At least one public body must be provided."):
        use_case.execute(application.laa_reference, public_body_ids)

    use_case.update_public_bodies_port.update_public_bodies.assert_not_called()
    use_case.update_public_bodies_port.commit.assert_not_called()
    use_case.update_public_bodies_port.rollback.assert_not_called()


def test_update_public_bodies_raises_exception_on_application_not_found(
    use_case,
    application,
):
    public_body_ids = [PublicBodyId.DEPARTMENT_FOR_TRANSPORT]

    use_case.application_lookup_port.get_application_by_laa_reference.return_value = (
        None
    )

    with pytest.raises(
        ApplicationNotFoundError,
        match=f"Application {application.laa_reference} not found",
    ):
        use_case.execute(application.laa_reference, public_body_ids)

    use_case.update_public_bodies_port.update_public_bodies.assert_not_called()
    use_case.update_public_bodies_port.commit.assert_not_called()
    use_case.update_public_bodies_port.rollback.assert_not_called()


def test_update_public_bodies_rolls_back_on_exception_during_update(
    use_case,
    application,
):
    public_body_ids = [PublicBodyId.DEPARTMENT_FOR_TRANSPORT]

    use_case.update_public_bodies_port.update_public_bodies.side_effect = Exception(
        "Error updating public bodies"
    )

    with pytest.raises(Exception, match="Error updating public bodies"):
        use_case.execute(application.laa_reference, public_body_ids)

    use_case.update_public_bodies_port.update_public_bodies.assert_called_once_with(
        application=application,
        public_body_ids=public_body_ids,
    )
    use_case.update_public_bodies_port.commit.assert_not_called()
    use_case.update_public_bodies_port.rollback.assert_called_once()
