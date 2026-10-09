-- Seed application INQ-202-000 (Ginny Weasley) with a single SUBMITTED nil bill claim.
-- Run via psql through laa-inquest-dev RDS db's port-forward pod and review the
-- dry-run output (w ROLLBACK on the last line) before running with COMMIT.
-- Requires reference data from bin/seed.py (proceeding IQPC, public body MINISTRY_OF_DEFENCE).
-- A nil bill takes no evidence file or cost template, so no psql variables are needed.
BEGIN;

-- 0. Replace any earlier seed of this application. Refuses to touch an application that
-- was not created by this script (identified by its seed coroners letter).
DO $$
DECLARE
  v_application_id integer;
  v_client_id integer;
  v_deceased_id integer;
  v_provider_id integer;
  v_coroners_letter_id uuid;
  v_correspondence_address_id integer;
  v_home_address_id integer;
  v_is_seeded boolean;
BEGIN
  SELECT a.application_id, a.client_id, a.deceased_id, a.provider_id, a.coroners_letter_id,
         cl.sds_file_name = 'seed-inq-202-000-coroners-letter'
  INTO v_application_id, v_client_id, v_deceased_id, v_provider_id, v_coroners_letter_id, v_is_seeded
  FROM application a
  LEFT JOIN coroners_letter cl ON cl.coroners_letter_id = a.coroners_letter_id
  WHERE a.laa_reference = 'INQ-202-000';

  IF v_application_id IS NULL THEN
    RETURN;
  END IF;
  IF v_is_seeded IS NOT TRUE THEN
    RAISE EXCEPTION 'Application INQ-202-000 exists but was not created by this script';
  END IF;

  SELECT correspondence_address_id, home_address_id
  INTO v_correspondence_address_id, v_home_address_id
  FROM client
  WHERE client_id = v_client_id;

  DELETE FROM history_event WHERE application_id = v_application_id;
  DELETE FROM decision_reason WHERE claim_decision_id IN (
    SELECT claim_decision_id FROM claim_decision WHERE claim_id IN (
      SELECT claim_id FROM claim WHERE application_id = v_application_id));
  DELETE FROM claim_decision_amount WHERE claim_decision_id IN (
    SELECT claim_decision_id FROM claim_decision WHERE claim_id IN (
      SELECT claim_id FROM claim WHERE application_id = v_application_id));
  DELETE FROM claim_decision WHERE claim_id IN (
    SELECT claim_id FROM claim WHERE application_id = v_application_id);
  DELETE FROM claim_payment_extract WHERE claim_id IN (
    SELECT claim_id FROM claim WHERE application_id = v_application_id);
  DELETE FROM claim_inquest_outcome WHERE claim_id IN (
    SELECT claim_id FROM claim WHERE application_id = v_application_id);
  -- The cost template file is an unlinked claim_evidence row, so it is removed by id.
  DELETE FROM claim_evidence WHERE claim_evidence_id IN (
    SELECT claim_cost_template_file_id FROM claim_cost_template WHERE claim_id IN (
      SELECT claim_id FROM claim WHERE application_id = v_application_id));
  DELETE FROM claim_cost_template WHERE claim_id IN (
    SELECT claim_id FROM claim WHERE application_id = v_application_id);
  DELETE FROM claim_evidence WHERE claim_id IN (
    SELECT claim_id FROM claim WHERE application_id = v_application_id);
  DELETE FROM claim WHERE application_id = v_application_id;
  DELETE FROM application_public_body WHERE application_id = v_application_id;
  DELETE FROM application_proceeding WHERE application_id = v_application_id;
  DELETE FROM application WHERE application_id = v_application_id;
  DELETE FROM deceased WHERE deceased_id = v_deceased_id;
  DELETE FROM client WHERE client_id = v_client_id;
  DELETE FROM address WHERE address_id IN (v_correspondence_address_id, v_home_address_id);
  DELETE FROM provider WHERE provider_id = v_provider_id;
  DELETE FROM coroners_letter WHERE coroners_letter_id = v_coroners_letter_id;
END $$;

-- 1. Granted application with its client, deceased, provider, letter and proceeding.
DO $$
DECLARE
  v_coroners_letter_id uuid := gen_random_uuid();
  v_correspondence_address_id integer;
  v_home_address_id integer;
  v_client_id integer;
  v_deceased_id integer;
  v_provider_id integer;
  v_application_id integer;
BEGIN
  INSERT INTO coroners_letter (coroners_letter_id, sds_file_name, file_name)
  VALUES (v_coroners_letter_id, 'seed-inq-202-000-coroners-letter', 'coroners-letter.pdf');

  INSERT INTO address (address_line_1, address_line_2, town_or_city, county, postcode)
  VALUES ('34 Example Street', NULL, 'Bristol', 'Bristol', 'BS1 1AA')
  RETURNING address_id INTO v_correspondence_address_id;

  INSERT INTO address (address_line_1, address_line_2, town_or_city, county, postcode)
  VALUES ('34 Example Street', NULL, 'Bristol', 'Bristol', 'BS1 1AA')
  RETURNING address_id INTO v_home_address_id;

  INSERT INTO client (
    client_first_name, client_last_name, date_of_birth, national_insurance_number,
    has_applied_previously, has_no_fixed_abode, correspondence_address_source,
    correspondence_address_id, home_address_id,
    correspondence_recipient_type, correspondence_recipient_name
  )
  VALUES (
    'Ginny', 'Weasley', '1992-08-11', 'DD123456E',
    false, false, 'USE_SPECIFIED_ADDRESS',
    v_correspondence_address_id, v_home_address_id,
    'PERSON', 'Ginny Weasley'
  )
  RETURNING client_id INTO v_client_id;

  -- The inquest body has no dedicated column, so it is held in coroners_reference.
  INSERT INTO deceased (
    deceased_first_name, deceased_last_name, deceased_date_of_birth, deceased_date_of_death,
    coroners_reference, further_information, client_relationship_to_deceased, client_id
  )
  VALUES (
    'Arthur', 'Weasley', '1955-01-01', '2025-09-01',
    'Bristol Coroner office', 'Further information.', 'Parent', v_client_id
  )
  RETURNING deceased_id INTO v_deceased_id;

  INSERT INTO provider (firm_code, office_id, email_address)
  VALUES ('1473', '0U651L', 'nil.bill@example.com')
  RETURNING provider_id INTO v_provider_id;

  INSERT INTO application (
    laa_reference, created_at, updated_at, status, used_delegated_functions,
    application_type, auto_grant, client_id, deceased_id, provider_id, coroners_letter_id
  )
  VALUES (
    'INQ-202-000', '2025-10-01 09:00:00+00', '2025-10-01 09:00:00+00', 'LIVE', true,
    'INITIAL', true, v_client_id, v_deceased_id, v_provider_id, v_coroners_letter_id
  )
  RETURNING application_id INTO v_application_id;

  INSERT INTO application_proceeding (
    client_involvement_type, merits_decision, application_id, proceeding_id,
    certificate_issue_date, certificate_start_date
  )
  VALUES (
    'RESPONDENT', 'GRANTED', v_application_id, 'IQPC',
    DATE '2025-10-01', DATE '2025-10-01'
  );

  INSERT INTO application_public_body (public_body_id, application_id)
  VALUES ('MINISTRY_OF_DEFENCE', v_application_id);
END $$;

-- 2. Nil bill: zero gross, no net or VAT-zero total, no counsel details, no recovery.
INSERT INTO claim (
  application_id, claim_reference, claim_type_id, status_id, submission_date,
  total_profit_cost_gross, total_funds_remaining_after_claim, claimant_id,
  has_alternative_funding, has_recovery_costs_awarded,
  financial_recovery_previous_pre_certificate_costs, financial_recovery_cost,
  financial_recovery_damages, financial_recovery_interest, paying_party
)
SELECT
  a.application_id, 'INQC-202A-0001', 'NIL_BILL'::claimtype, 'SUBMITTED'::claimstatus,
  '2026-10-05 09:00:00+00', 0.00, 10000.00, 'nil.bill@example.com',
  false, false,
  0.00, 0.00, 0.00, 0.00, 'N/A'
FROM application a
WHERE a.laa_reference = 'INQ-202-000';

INSERT INTO claim_inquest_outcome (claim_id, inquest_outcome_id)
SELECT claim_id, 'ACCIDENT_OR_MISADVENTURE'::inquestoutcomecode
FROM claim
WHERE claim_reference = 'INQC-202A-0001';

-- 3. Application history: submitted, assessed, certificate created, grant email and letter.
INSERT INTO history_event (event_reference, timestamp, actor, actor_type, event_data, application_id)
SELECT
  e.event_reference::historyeventreference, e.event_timestamp::timestamptz, e.actor,
  e.actor_type::actortype, e.event_data::json, a.application_id
FROM (VALUES
  ('APPLICATION_SUBMITTED', '2025-10-01 09:00:00+00', 'nil.bill@example.com', 'PROVIDER', NULL),
  ('APPLICATION_SUBMISSION_CONFIRMATION', '2025-10-01 09:00:05+00', 'System', 'SYSTEM',
    '{"recipient": "nil.bill@example.com", "channel": "email"}'),
  ('APPLICATION_ASSESSMENT_COMPLETED', '2025-10-01 10:00:00+00', 'Seed Caseworker', 'CASEWORKER',
    '{"merits_decision": "Granted"}'),
  ('CERTIFICATE_CREATED', '2025-10-01 10:00:01+00', 'Seed Caseworker', 'CASEWORKER',
    '{"laa_reference": "INQ-202-000"}'),
  ('APPLICATION_GRANTED_EMAIL', '2025-10-01 10:00:02+00', 'System', 'SYSTEM',
    '{"recipient": "nil.bill@example.com", "channel": "email"}'),
  ('APPLICATION_GRANTED_LETTER', '2025-10-01 10:00:03+00', 'System', 'SYSTEM',
    '{"recipient": {"address_line_1": "c/o Ginny Weasley 34 Example Street", "address_line_2": null, "town_or_city": "Bristol", "county": "Bristol", "postcode": "BS1 1AA"}, "channel": "letter"}')
) AS e(event_reference, event_timestamp, actor, actor_type, event_data)
CROSS JOIN application a
WHERE a.laa_reference = 'INQ-202-000';

-- 4. Claim history: submitted and confirmation email.
INSERT INTO history_event (event_reference, timestamp, actor, actor_type, event_data, application_id)
SELECT
  e.event_reference::historyeventreference,
  c.submission_date + e.delay,
  CASE WHEN e.actor_type = 'PROVIDER' THEN c.claimant_id ELSE 'System' END,
  e.actor_type::actortype,
  CASE e.event_reference
    WHEN 'CLAIM_SUBMITTED' THEN jsonb_build_object(
      'claim_type', c.claim_type_id::text, 'claim_reference', c.claim_reference)
    ELSE jsonb_build_object('recipient', p.email_address, 'channel', 'email')
  END::json,
  c.application_id
FROM claim c
JOIN application a ON a.application_id = c.application_id
JOIN provider p ON p.provider_id = a.provider_id
CROSS JOIN (VALUES
  ('CLAIM_SUBMITTED', 'PROVIDER', interval '0 seconds'),
  ('CLAIM_SUBMISSION_CONFIRMATION', 'SYSTEM', interval '5 seconds')
) AS e(event_reference, actor_type, delay)
WHERE a.laa_reference = 'INQ-202-000';

-- 5. Expect 1 SUBMITTED NIL_BILL claim with 0.00 gross.
SELECT
  c.claim_reference, c.claim_type_id, c.status_id, c.submission_date::date,
  c.total_profit_cost_net, c.total_profit_cost_gross, c.total_profit_cost_vat_zero,
  c.total_funds_remaining_after_claim
FROM claim c
JOIN application a ON a.application_id = c.application_id
WHERE a.laa_reference = 'INQ-202-000';

-- Expect 8 events: 6 for the application and 2 for the claim.
SELECT h.timestamp, h.event_reference, h.actor_type, h.actor, h.event_data
FROM history_event h
JOIN application a ON a.application_id = h.application_id
WHERE a.laa_reference = 'INQ-202-000'
ORDER BY h.timestamp, h.id;

-- Only swap to COMMIT once both result sets look correct.
ROLLBACK;
-- COMMIT;
