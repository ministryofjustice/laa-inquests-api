import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application, Provider
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ClaimType
from app.models.claim.index import Claim, ClaimDecision, ClaimEvidence, DecisionReason
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.models.notifications.enums import NotificationType


def _make_request_body(overrides=None):
    body = {
        "claimType": "PAYMENT_ON_ACCOUNT",
        "totalProfitCostNet": 1000,
        "totalProfitCostGross": 1200,
        "poaTypeId": "PROFIT_COST",
        "claimantId": "claimant-123@provider.co.uk",
        "claimEvidenceIds": [str(uuid.uuid4())],
    }
    if overrides is not None:
        body.update(overrides)
    return body


def _seed_approved_claim(
    session,
    laa_reference: int,
    decision: ClaimDecisionStatus,
    gross: Decimal | None = None,
    vat_zero: Decimal | None = None,
) -> Claim:
    claim = Claim(
        laa_reference=laa_reference,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=ClaimStatus.PAY_IN_FULL,
        submission_date=datetime.now(UTC),
        total_profit_cost_gross=gross,
        total_profit_cost_vat_zero=vat_zero,
        total_funds_remaining_after_claim=Decimal(0),
        poa_type_id=None,
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    session.add(ClaimDecision(claim_id=claim.claim_id, decision=decision))
    session.commit()
    return claim


def test_404_create_claim_when_application_belongs_to_another_firm(
    session, client, auth_token
):
    other_provider = Provider(
        firm_code="ZZ999Z",
        office_id="002",
        email_address="other@example.com",
    )
    session.add(other_provider)
    session.commit()
    session.refresh(other_provider)

    existing = session.exec(select(Application)).first()
    other_application = Application(
        client_id=existing.client_id,
        deceased_id=existing.deceased_id,
        provider_id=other_provider.provider_id,
    )
    session.add(other_application)
    session.commit()
    session.refresh(other_application)

    response = client.post(
        f"/applications/{other_application.laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_201_create_claim_response_contains_only_claim_id_when_not_rejected(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert isinstance(claim["claimId"], int)
    assert set(claim.keys()) == {"claimId"}


def test_201_create_claim_sends_submission_confirmation_email_to_provider(
    session, client, auth_token, mock_gov_notify
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    mock_gov_notify.send_claim_submit_confirmation_email.assert_called_once()

    call_kwargs = mock_gov_notify.send_claim_submit_confirmation_email.call_args.kwargs
    claim = call_kwargs["claim"]
    application = call_kwargs["application"]
    recipient_email = call_kwargs["recipient_email"]
    assert claim.laa_reference == laa_reference
    assert application.laa_reference == laa_reference
    assert recipient_email == application.provider.email_address


def test_201_create_claim_creates_submission_confirmation_comms_history_event(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201

    history_event = session.exec(
        select(HistoryEvent).where(
            (HistoryEvent.laa_reference == laa_reference)
            & (
                HistoryEvent.event_reference
                == HistoryEventReference.CLAIM_SUBMISSION_CONFIRMATION
            )
        )
    ).one()

    assert (
        history_event.event_reference
        == HistoryEventReference.CLAIM_SUBMISSION_CONFIRMATION
    )
    assert history_event.actor == ActorType.SYSTEM
    assert history_event.actor_type == ActorType.SYSTEM
    assert history_event.event_data == {
        "recipient": application.provider.email_address,
        "channel": NotificationType.EMAIL,
    }
    assert history_event.laa_reference == laa_reference


def test_201_create_claim_creates_claim_submitted_history_event(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference
    request_body = _make_request_body()

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201

    history_event = session.exec(
        select(HistoryEvent).where(
            (HistoryEvent.laa_reference == laa_reference)
            & (HistoryEvent.event_reference == HistoryEventReference.CLAIM_SUBMITTED)
        )
    ).one()

    assert history_event.event_reference == HistoryEventReference.CLAIM_SUBMITTED
    assert history_event.actor == request_body["claimantId"]
    assert history_event.actor_type == ActorType.PROVIDER
    assert history_event.event_data == {"claim_type": request_body["claimType"]}
    assert history_event.laa_reference == laa_reference


def test_201_create_claim_auto_approves_payment_on_account_when_eligible(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId"}

    stored_claim = session.get(Claim, claim["claimId"])
    assert stored_claim is not None
    assert stored_claim.status_id == "PAY_IN_FULL"

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim["claimId"])
    ).first()
    assert decision is not None
    assert decision.decision == "PAY_IN_FULL"


def test_201_create_claim_stores_provisional_total_funds_remaining_for_approved_claim(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim_id = response.json()["claimId"]

    stored_claim = session.get(Claim, claim_id)
    assert stored_claim.status_id == "PAY_IN_FULL"
    assert stored_claim.total_funds_remaining_after_claim == Decimal("8800.00")


def test_201_create_claim_deducts_new_claim_amount_from_total_funds_available_when_not_approved(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"claimType": "FINAL_BILL", "poaTypeId": None, "claimantId": None}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim_id = response.json()["claimId"]

    stored_claim = session.get(Claim, claim_id)
    assert stored_claim.status_id != "PAY_IN_FULL"
    # 10000 limit - 1200 new claim requested gross = 8800
    assert stored_claim.total_funds_remaining_after_claim == Decimal("8800.00")


def test_201_create_claim_deducts_cumulative_approved_and_new_claim_amount(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_approved_claim(
        session,
        laa_reference,
        ClaimDecisionStatus.GRANT,
        gross=Decimal("2000.00"),
    )
    _seed_approved_claim(
        session,
        laa_reference,
        ClaimDecisionStatus.PAY_IN_FULL,
        vat_zero=Decimal("1500.00"),
    )

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 800, "totalProfitCostGross": 1000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim_id = response.json()["claimId"]

    # 10000 limit - (2000 + 1500 approved) - 1000 new claim requested = 5500
    stored_claim = session.get(Claim, claim_id)
    assert stored_claim.total_funds_remaining_after_claim == Decimal("5500.00")

    get_response = client.get(
        f"/applications/{laa_reference}/claims/{claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["totalFundsRemainingAfterClaim"] == "5500.00"


def test_201_created_claim_returns_total_funds_remaining_on_get_by_id(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    create_response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    claim_id = create_response.json()["claimId"]

    get_response = client.get(
        f"/applications/{laa_reference}/claims/{claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert get_response.status_code == 200
    assert get_response.json()["totalFundsRemainingAfterClaim"] == "8800.00"


def test_201_create_claim_without_optional_fields(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"claimType": "FINAL_BILL", "poaTypeId": None, "claimantId": None}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId"}


def test_201_create_claim_persists_claim_to_database(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    claim_id = response.json()["claimId"]
    stored_claim = session.get(Claim, claim_id)
    assert stored_claim is not None
    assert stored_claim.laa_reference == laa_reference


def test_201_create_claim_links_provided_evidence_ids_to_claim(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    evidence = ClaimEvidence(sds_file_name="stored.pdf", file_name="original.pdf")
    session.add(evidence)
    session.commit()
    session.refresh(evidence)

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"claimEvidenceIds": [str(evidence.claim_evidence_id)]}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim_id = response.json()["claimId"]
    stored_evidence = session.get(ClaimEvidence, evidence.claim_evidence_id)
    assert stored_evidence.claim_id == claim_id


def test_422_create_claim_with_empty_evidence_ids_returns_error(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body({"claimEvidenceIds": []}),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "MISSING_CLAIM_EVIDENCE"


def test_422_payment_on_account_without_poa_type_id(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body({"poaTypeId": None}),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]["errorCode"]
        == "MISSING_POA_TYPE_FOR_PAYMENT_ON_ACCOUNT"
    )


def test_422_non_payment_on_account_with_poa_type_id(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"claimType": "FINAL_BILL", "poaTypeId": "PROFIT_COST"}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]["errorCode"]
        == "POA_TYPE_NOT_ALLOWED_FOR_NON_PAYMENT_ON_ACCOUNT"
    )


def test_422_profit_cost_with_no_cost_fields(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": None,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "MISSING_TOTAL_CLAIM_COST"


def test_422_profit_cost_with_net_higher_than_gross(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 1200, "totalProfitCostGross": 1000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "NET_TOTAL_HIGHER_THAN_GROSS_TOTAL"


def test_201_profit_cost_with_vat_zero_only(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": 500,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201


def test_422_profit_cost_mixing_vat_zero_and_net(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 1000, "totalProfitCostVatZero": 500}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "PROFIT_COST_MIXED_VAT"


def test_201_non_profit_cost_with_vat_zero_only_defaults_missing_totals(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "poaTypeId": "EXPERT_COST",
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": "150.00",
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId"}

    stored_claim = session.get(Claim, claim["claimId"])
    assert stored_claim is not None
    assert Decimal(str(stored_claim.total_profit_cost_net)) == Decimal("0.00")
    assert Decimal(str(stored_claim.total_profit_cost_gross)) == Decimal("0.00")
    assert Decimal(str(stored_claim.total_profit_cost_vat_zero)) == Decimal("150.00")


def test_422_non_profit_cost_with_no_cost_fields(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "poaTypeId": "EXPERT_COST",
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": None,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "MISSING_NON_PROFIT_COST_TOTAL"
    assert (
        response.json()["detail"]["message"]
        == "Please complete the total value of your claim to continue"
    )


def test_422_non_profit_cost_with_net_higher_than_gross(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "poaTypeId": "NON_EXPERT_DISBURSEMENT",
                "totalProfitCostNet": "120.00",
                "totalProfitCostGross": "100.00",
                "totalProfitCostVatZero": None,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "NET_TOTAL_HIGHER_THAN_GROSS_TOTAL"
    assert (
        response.json()["detail"]["message"]
        == "Net total cannot be higher than the gross total value"
    )


def test_201_create_claim_when_existing_claims_push_application_total_over_limit(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 6000, "totalProfitCostGross": 6000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 5000, "totalProfitCostGross": 6000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201


def test_201_create_claim_auto_reject_returns_reason_and_updates_decision_status(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    for _ in range(4):
        seed_response = client.post(
            f"/applications/{laa_reference}/claim",
            json=_make_request_body(
                {
                    "totalProfitCostNet": 1,
                    "totalProfitCostGross": 1,
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert seed_response.status_code == 201

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": 1,
                "totalProfitCostGross": 1,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId", "rejectionReasons"}
    assert claim["rejectionReasons"] == ["MAX_POA_CLAIMS_EXCEEDED"]

    claim_id = claim["claimId"]
    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)
    ).first()
    assert decision is not None
    assert decision.decision == "REJECT"

    decision_reasons = session.exec(
        select(DecisionReason).where(
            DecisionReason.claim_decision_id == decision.claim_decision_id
        )
    ).all()
    assert len(decision_reasons) == 1
    assert decision_reasons[0].reason_code == "MAX_POA_CLAIMS_EXCEEDED"


def test_201_create_claim_does_not_count_rejected_profit_cost_poa_towards_max_limit(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    seeded_claim_ids = []
    for _ in range(4):
        seed_response = client.post(
            f"/applications/{laa_reference}/claim",
            json=_make_request_body(
                {
                    "totalProfitCostNet": 1,
                    "totalProfitCostGross": 1,
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert seed_response.status_code == 201
        seeded_claim_ids.append(seed_response.json()["claimId"])

    claim_to_reject = session.get(Claim, seeded_claim_ids[0])
    claim_to_reject.status_id = "REJECTED"
    session.add(claim_to_reject)
    session.commit()

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": 1,
                "totalProfitCostGross": 1,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId"}
    assert "rejectionReasons" not in claim

    claim_id = claim["claimId"]
    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)
    ).first()
    assert decision is not None
    assert decision.decision == "PAY_IN_FULL"


def test_201_create_claim_that_passes_rejection_rules_auto_approves(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": 1,
                "totalProfitCostGross": 1,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId"}
    assert "rejectionReasons" not in claim

    claim_id = claim["claimId"]
    stored_claim = session.get(Claim, claim_id)
    assert stored_claim is not None
    assert stored_claim.status_id == "PAY_IN_FULL"

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)
    ).first()
    assert decision is not None
    assert decision.decision == "PAY_IN_FULL"


def test_201_create_claim_does_not_auto_approve_when_amount_exceeds_50000(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    application_proceeding = application.proceeding
    application_proceeding.proceeding.substantive_cost_limitation = 999999
    application_proceeding.certificate_start_date = datetime(2000, 1, 1, tzinfo=UTC)
    session.add(application_proceeding.proceeding)
    session.add(application_proceeding)
    session.commit()

    response = client.post(
        f"/applications/{application.laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": 50000.01,
                "totalProfitCostGross": 50000.01,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId"}

    stored_claim = session.get(Claim, claim["claimId"])
    assert stored_claim is not None
    assert stored_claim.status_id == "SUBMITTED"

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim["claimId"])
    ).first()
    assert decision is None


def test_201_create_claim_does_not_auto_approve_when_application_status_is_withdrawn(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    application_proceeding = application.proceeding
    application_proceeding.proceeding.substantive_cost_limitation = 999999
    application_proceeding.certificate_start_date = datetime(2000, 1, 1, tzinfo=UTC)
    application.status = "WITHDRAWN"
    session.add(application_proceeding.proceeding)
    session.add(application_proceeding)
    session.add(application)
    session.commit()

    response = client.post(
        f"/applications/{application.laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": 50000,
                "totalProfitCostGross": 50000,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId"}

    stored_claim = session.get(Claim, claim["claimId"])
    assert stored_claim is not None
    assert stored_claim.status_id == "SUBMITTED"

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim["claimId"])
    ).first()
    assert decision is None


def test_422_create_claim_when_application_not_granted(session, client, auth_token):
    application = session.exec(select(Application)).first()
    application.proceeding.merits_decision = MeritsDecision.PENDING
    session.add(application.proceeding)
    session.commit()

    response = client.post(
        f"/applications/{application.laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": 1000,
                "totalProfitCostGross": 1200,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "APPLICATION_NOT_GRANTED"

    stored_claims = session.exec(
        select(Claim).where(Claim.laa_reference == application.laa_reference)
    ).all()
    assert stored_claims == []


def test_201_create_claim_auto_reject_returns_multiple_reasons_for_rejection_when_applicable(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference
    application.proceeding.merits_decision = MeritsDecision.GRANTED
    session.add(application.proceeding)
    session.commit()

    for _ in range(4):
        seed_response = client.post(
            f"/applications/{laa_reference}/claim",
            json=_make_request_body(
                {
                    "totalProfitCostNet": 1,
                    "totalProfitCostGross": 1,
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert seed_response.status_code == 201
        assert set(seed_response.json().keys()) == {"claimId"}

    application = session.exec(
        select(Application).where(Application.laa_reference == laa_reference)
    ).first()
    application_proceeding = application.proceeding
    application_proceeding.proceeding.substantive_cost_limitation = 5
    application_proceeding.certificate_start_date = datetime.now(tz=UTC).date()
    application_proceeding.merits_decision = MeritsDecision.GRANTED
    session.add(application_proceeding.proceeding)
    session.add(application_proceeding)
    session.commit()

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": 10,
                "totalProfitCostGross": 10,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert set(claim.keys()) == {"claimId", "rejectionReasons"}

    expected_reasons = {
        "MAX_POA_CLAIMS_EXCEEDED",
        "CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT",
        "APPLICATION_CLAIMS_EXCEED_COST_LIMIT",
        "PROFIT_COST_POA_CLAIM_SUBMITTED_TOO_EARLY",
    }
    assert set(claim["rejectionReasons"]) == expected_reasons
    assert len(claim["rejectionReasons"]) == 4

    claim_id = claim["claimId"]
    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)
    ).first()
    assert decision is not None
    assert decision.decision == "REJECT"

    decision_reasons = session.exec(
        select(DecisionReason).where(
            DecisionReason.claim_decision_id == decision.claim_decision_id
        )
    ).all()
    assert len(decision_reasons) == 4
    assert {r.reason_code for r in decision_reasons} == expected_reasons


def test_201_create_claim_auto_approves_subsequent_claim_after_one_is_rejected(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference
    application.proceeding.merits_decision = MeritsDecision.GRANTED
    session.add(application.proceeding)
    session.commit()

    rejected_response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 12000, "totalProfitCostGross": 12000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    assert rejected_response.status_code == 201
    rejected_claim = rejected_response.json()
    assert "CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT" in rejected_claim["rejectionReasons"]
    rejected_stored = session.get(Claim, rejected_claim["claimId"])
    assert rejected_stored.status_id == "REJECTED"

    approved_response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 5000, "totalProfitCostGross": 5000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert approved_response.status_code == 201
    approved_claim = approved_response.json()
    assert set(approved_claim.keys()) == {"claimId"}

    approved_stored = session.get(Claim, approved_claim["claimId"])
    assert approved_stored.status_id == "PAY_IN_FULL"


def test_201_create_claim_rejects_when_cumulative_approved_claims_exceed_limit(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference
    application.proceeding.merits_decision = MeritsDecision.GRANTED
    session.add(application.proceeding)
    session.commit()

    for gross in (7000, 2000):
        approved = client.post(
            f"/applications/{laa_reference}/claim",
            json=_make_request_body(
                {"totalProfitCostNet": gross, "totalProfitCostGross": gross}
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert approved.status_code == 201
        assert set(approved.json().keys()) == {"claimId"}

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 2000, "totalProfitCostGross": 2000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert "APPLICATION_CLAIMS_EXCEED_COST_LIMIT" in claim["rejectionReasons"]
