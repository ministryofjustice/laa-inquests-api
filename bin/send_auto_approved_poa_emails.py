import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.adapters.gov_notify import GovNotifyAdapter
from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.adapters.provider_details_adapter import ProviderDetailsAdapter
from app.config import Config
from app.db import CustomSessionLocal
from app.use_cases.send_auto_approved_poa_claim_emails import (
    SendAutoApprovedPoaClaimEmailsUseCase,
)


def send_auto_approved_poa_emails() -> None:
    """Send deferred grant emails for POA claims auto-approved the previous day."""
    with CustomSessionLocal() as session:
        claim_repository = ClaimRepositoryAdapter(session=session)
        history_events = HistoryEventRepositoryAdapter(session=session)
        provider_details = ProviderDetailsAdapter(
            base_url=Config.PROVIDER_API_BASE_URL,
            api_key=Config.PROVIDER_API_KEY,
        )
        gov_notify = GovNotifyAdapter()

        use_case = SendAutoApprovedPoaClaimEmailsUseCase(
            list_auto_approved_poa_claims_port=claim_repository,
            get_application_history_port=history_events,
            create_history_event_port=history_events,
            provider_details_port=provider_details,
            gov_notify_port=gov_notify,
        )
        use_case.execute()


if __name__ == "__main__":
    send_auto_approved_poa_emails()
