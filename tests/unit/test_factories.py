"""Fails first when a model change needs a factory default updated."""

import pytest
from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from app.models.claim.enums import InquestOutcomeCode
from tests.factories import builders, domain
from tests.factories.persisted import (
    application_by_reference,
    create_application,
    create_claim,
    create_claim_cost_template,
    create_claim_decision,
    create_claim_evidence,
    create_claim_inquest_outcomes,
    create_coroners_letter,
    create_history_event,
    create_payment_extracts,
)
from tests.factories.seed import SEED_LAA_REFERENCE


@pytest.mark.parametrize(
    "build",
    [
        builders.build_home_address,
        builders.build_correspondence_address,
        builders.build_office_address,
        builders.build_client,
        builders.build_deceased,
        builders.build_provider,
        builders.build_proceeding,
        builders.build_public_body,
        builders.build_application_proceeding,
        builders.build_application_public_body,
        builders.build_coroners_letter,
        builders.build_application,
        builders.build_claim,
        builders.build_poa_claim,
        builders.build_nil_bill_claim,
        builders.build_claim_evidence,
        builders.build_claim_decision,
        builders.build_decision_reason,
        builders.build_claim_inquest_outcome,
        builders.build_claim_cost_template,
        builders.build_claim_payment_extract,
        builders.build_granted_application,
        builders.build_history_event,
        builders.build_certificate,
        domain.build_domain_claim,
        domain.build_final_bill_domain_claim,
        domain.build_nil_bill_domain_claim,
        domain.build_existing_claim_summary,
        domain.build_domain_claim_evidence,
        domain.build_domain_coroners_letter,
        domain.build_pay_in_full_claim,
    ],
)
def test_builder_constructs_with_defaults(build):
    assert build() is not None


def test_seeded_application_is_available(seeded_application):
    assert seeded_application.laa_reference == SEED_LAA_REFERENCE


# TODO: Review whether this test is necessary. We are testing the test fixture here, rather than application behaviour
def test_create_application_persists_full_tree(session):
    application = create_application(session)

    stored = session.exec(
        select(Application).where(
            Application.laa_reference == application.laa_reference
        )
    ).one()
    assert stored.client.home_address is not None
    assert stored.deceased.client_id == stored.client_id
    assert stored.provider is not None
    assert stored.proceeding.proceeding.proceeding_id == "IQOT"
    assert len(stored.public_bodies) == 1


def test_create_application_generates_unique_references(session):
    first = create_application(session)
    second = create_application(session)

    assert first.laa_reference != second.laa_reference


def test_create_claim_and_children_persist(session, seeded_application):
    claim = create_claim(session, seeded_application, preset=builders.build_poa_claim)
    evidence = create_claim_evidence(session, claim)
    decision = create_claim_decision(session, claim, reasons=[{}])
    extracts = create_payment_extracts(session, claim)
    outcomes = create_claim_inquest_outcomes(
        session, claim, [InquestOutcomeCode.NATURAL_CAUSES]
    )
    cost_template = create_claim_cost_template(session, claim)

    assert claim.claim_id is not None
    assert evidence.claim_id == claim.claim_id
    assert len(decision.decision_reasons) == 1
    assert [e.sequence_number for e in extracts] == [1, 2]
    assert [o.claim_id for o in outcomes] == [claim.claim_id]
    assert cost_template.claim_id == claim.claim_id


def test_application_by_reference_returns_seeded_application(session):
    application = application_by_reference(session, SEED_LAA_REFERENCE)

    assert application.laa_reference == SEED_LAA_REFERENCE


def test_create_coroners_letter_persists(session):
    letter = create_coroners_letter(session)

    assert letter.coroners_letter_id is not None


def test_create_history_event_persists(session, seeded_application):
    event = create_history_event(session, seeded_application)

    assert event.application_id == seeded_application.application_id


def test_create_application_applies_dedicated_substantive_cost_limitation(
    session, seeded_application
):
    seeded_limit = seeded_application.proceeding.proceeding.substantive_cost_limitation
    first = create_application(
        session,
        proceeding_overrides={"merits_decision": MeritsDecision.GRANTED},
        substantive_cost_limitation=5,
    )
    second = create_application(
        session,
        proceeding_overrides={"merits_decision": MeritsDecision.GRANTED},
        substantive_cost_limitation=7,
    )

    assert first.proceeding.substantive_cost_limitation == 5
    assert second.proceeding.substantive_cost_limitation == 7
    assert (
        seeded_application.proceeding.proceeding.substantive_cost_limitation
        == seeded_limit
    )
