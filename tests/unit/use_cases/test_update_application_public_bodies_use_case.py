from unittest.mock import MagicMock

import pytest

from app.contexts.user import set_entra_user_context
from app.models.application.enums import MeritsDecision, PublicBodyId
from app.models.application.index import (
    Application,
)
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.update_application_public_bodies_port import ApplicationPublicBodiesPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ApplicationNotGrantedError,
)
from app.use_cases.update_public_bodies import UpdatePublicBodiesUseCase
from tests.unit.factories import create_base_application


@pytest.fixture(autouse=True)
def entra_user_context() -> None:
    set_entra_user_context(None, "Caseworker")


@pytest.fixture
def application() -> Application:
    application = create_base_application()
    application.proceeding.merits_decision = MeritsDecision.GRANTED
    return application


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
def create_history_event_port() -> MagicMock:
    return MagicMock(spec=CreateHistoryEventPort)


@pytest.fixture
def use_case(
    application_lookup_port: MagicMock,
    update_public_bodies_port: MagicMock,
    create_history_event_port: MagicMock,
) -> UpdatePublicBodiesUseCase:
    return UpdatePublicBodiesUseCase(
        application_lookup_port,
        update_public_bodies_port,
        create_history_event_port,
    )


def test_update_public_bodies_calls_ports_and_commits(
    use_case,
    application,
):
    public_body_ids = [PublicBodyId.DEPARTMENT_FOR_TRANSPORT]

    use_case.execute(application.laa_reference, public_body_ids)

    use_case.application_lookup_port.get_application_by_laa_reference.assert_called_once_with(
        application.laa_reference
    )
    use_case.update_public_bodies_port.update_public_bodies.assert_called_once_with(
        application=application,
        public_body_ids=public_body_ids,
    )
    use_case.update_public_bodies_port.commit.assert_called_once()
    use_case.update_public_bodies_port.rollback.assert_not_called()


@pytest.mark.parametrize(
    "merits_decision", [MeritsDecision.PENDING, MeritsDecision.REFUSED]
)
def test_update_public_bodies_raises_exception_when_application_not_granted(
    use_case,
    application,
    merits_decision,
):
    application.proceeding.merits_decision = merits_decision
    public_body_ids = [PublicBodyId.MINISTRY_OF_DEFENCE]

    with pytest.raises(
        ApplicationNotGrantedError,
        match=f"Application {application.laa_reference} is not granted",
    ):
        use_case.execute(application.laa_reference, public_body_ids)

    use_case.update_public_bodies_port.update_public_bodies.assert_not_called()
    use_case.create_history_event_port.create_history_event.assert_not_called()
    use_case.update_public_bodies_port.commit.assert_not_called()
    use_case.update_public_bodies_port.rollback.assert_not_called()


def test_update_public_bodies_creates_history_event(
    application_lookup_port,
    update_public_bodies_port,
    application,
):
    history_event_port = MagicMock(spec=CreateHistoryEventPort)
    use_case = UpdatePublicBodiesUseCase(
        application_lookup_port,
        update_public_bodies_port,
        history_event_port,
    )
    public_body_ids = [PublicBodyId.MINISTRY_OF_DEFENCE]

    use_case.execute(application.laa_reference, public_body_ids)

    history_event_port.create_history_event.assert_called_once_with(
        event_reference=HistoryEventReference.INTERESTED_PARTY_UPDATED,
        actor="Caseworker",
        actor_type=ActorType.CASEWORKER,
        laa_reference=application.laa_reference,
        event_data={
            "old_public_bodies": [PublicBodyId.DEPARTMENT_FOR_TRANSPORT],
            "new_public_bodies": public_body_ids,
        },
    )
    update_public_bodies_port.commit.assert_called_once()
    update_public_bodies_port.rollback.assert_not_called()


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


def test_update_public_bodies_rolls_back_on_history_event_creation_error(
    use_case,
    application,
):
    public_body_ids = [PublicBodyId.DEPARTMENT_FOR_TRANSPORT]
    use_case.create_history_event_port.create_history_event.side_effect = Exception(
        "Error creating history event"
    )

    with pytest.raises(Exception, match="Error creating history event"):
        use_case.execute(application.laa_reference, public_body_ids)

    use_case.update_public_bodies_port.update_public_bodies.assert_called_once_with(
        application=application,
        public_body_ids=public_body_ids,
    )
    use_case.update_public_bodies_port.commit.assert_not_called()
    use_case.update_public_bodies_port.rollback.assert_called_once()
