-- Seed application INQ-201-000 (Neville Longbottom) with a single SUBMITTED nil bill claim.
-- Run via psql through laa-inquest-dev RDS db's port-forward pod and review the
-- dry-run output (w ROLLBACK on the last line) before running with COMMIT.
-- Requires reference data from bin/seed.py (proceeding IQPC, public body DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE).
-- A nil bill takes no evidence file or cost template, so no psql variables are needed.
BEGIN;

-- 0. Abort if the application has already been seeded.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM application WHERE laa_reference = 'INQ-201-000') THEN
    RAISE EXCEPTION 'Application INQ-201-000 already exists';
  END IF;
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
  VALUES (v_coroners_letter_id, 'seed-inq-201-000-coroners-letter', 'coroners-letter.pdf');

  INSERT INTO address (address_line_1, address_line_2, town_or_city, county, postcode)
  VALUES ('12 Example Lane', NULL, 'Manchester', 'Greater Manchester', 'M1 1AA')
  RETURNING address_id INTO v_correspondence_address_id;

  INSERT INTO address (address_line_1, address_line_2, town_or_city, county, postcode)
  VALUES ('12 Example Lane', NULL, 'Manchester', 'Greater Manchester', 'M1 1AA')
  RETURNING address_id INTO v_home_address_id;

  INSERT INTO client (
    client_first_name, client_last_name, date_of_birth, national_insurance_number,
    has_applied_previously, has_no_fixed_abode, correspondence_address_source,
    correspondence_address_id, home_address_id,
    correspondence_recipient_type, correspondence_recipient_name
  )
  VALUES (
    'Neville', 'Longbottom', '1990-06-20', 'CC123456D',
    false, false, 'USE_SPECIFIED_ADDRESS',
    v_correspondence_address_id, v_home_address_id,
    'PERSON', 'Neville Longbottom'
  )
  RETURNING client_id INTO v_client_id;

  -- The inquest body has no dedicated column, so it is held in coroners_reference.
  INSERT INTO deceased (
    deceased_first_name, deceased_last_name, deceased_date_of_birth, deceased_date_of_death,
    coroners_reference, further_information, client_relationship_to_deceased, client_id
  )
  VALUES (
    'Augusta', 'Longbottom', '1940-01-01', '2025-08-01',
    'Manchester Coroner office', 'Further information.', 'Grandparent', v_client_id
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
    'INQ-201-000', '2025-09-01 09:00:00+00', '2025-09-01 09:00:00+00', 'LIVE', true,
    'INITIAL', true, v_client_id, v_deceased_id, v_provider_id, v_coroners_letter_id
  )
  RETURNING application_id INTO v_application_id;

  INSERT INTO application_proceeding (
    client_involvement_type, merits_decision, application_id, proceeding_id,
    certificate_issue_date, certificate_start_date
  )
  VALUES (
    'RESPONDENT', 'GRANTED', v_application_id, 'IQPC',
    DATE '2025-09-01', DATE '2025-09-01'
  );

  INSERT INTO application_public_body (public_body_id, application_id)
  VALUES ('DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE', v_application_id);
END $$;

-- 2. Nil bill: zero gross, no net or VAT-zero total, no counsel details; recovery costs awarded.
INSERT INTO claim (
  application_id, claim_reference, claim_type_id, status_id, submission_date,
  total_profit_cost_gross, total_funds_remaining_after_claim, claimant_id,
  has_alternative_funding, has_recovery_costs_awarded,
  financial_recovery_previous_pre_certificate_costs, financial_recovery_cost,
  financial_recovery_damages, financial_recovery_interest, paying_party
)
SELECT
  a.application_id, 'INQC-201A-0001', 'NIL_BILL'::claimtype, 'SUBMITTED'::claimstatus,
  '2026-10-05 09:00:00+00', 0.00, 10000.00, 'nil.bill@example.com',
  false, true,
  100.00, 250.00, 500.00, 25.00, 'Manchester City Council'
FROM application a
WHERE a.laa_reference = 'INQ-201-000';

INSERT INTO claim_inquest_outcome (claim_id, inquest_outcome_id)
SELECT claim_id, 'ACCIDENT_OR_MISADVENTURE'::inquestoutcomecode
FROM claim
WHERE claim_reference = 'INQC-201A-0001';

-- 3. Application history: submitted, assessed, certificate created, grant email and letter.
INSERT INTO history_event (event_reference, timestamp, actor, actor_type, event_data, application_id)
SELECT
  e.event_reference::historyeventreference, e.event_timestamp::timestamptz, e.actor,
  e.actor_type::actortype, e.event_data::json, a.application_id
FROM (VALUES
  ('APPLICATION_SUBMITTED', '2025-09-01 09:00:00+00', 'nil.bill@example.com', 'PROVIDER', NULL),
  ('APPLICATION_SUBMISSION_CONFIRMATION', '2025-09-01 09:00:05+00', 'System', 'SYSTEM',
    '{"recipient": "nil.bill@example.com", "channel": "email"}'),
  ('APPLICATION_ASSESSMENT_COMPLETED', '2025-09-01 10:00:00+00', 'Seed Caseworker', 'CASEWORKER',
    '{"merits_decision": "Granted"}'),
  ('CERTIFICATE_CREATED', '2025-09-01 10:00:01+00', 'Seed Caseworker', 'CASEWORKER',
    '{"laa_reference": "INQ-201-000"}'),
  ('APPLICATION_GRANTED_EMAIL', '2025-09-01 10:00:02+00', 'System', 'SYSTEM',
    '{"recipient": "nil.bill@example.com", "channel": "email"}'),
  ('APPLICATION_GRANTED_LETTER', '2025-09-01 10:00:03+00', 'System', 'SYSTEM',
    '{"recipient": {"address_line_1": "c/o Neville Longbottom 12 Example Lane", "address_line_2": null, "town_or_city": "Manchester", "county": "Greater Manchester", "postcode": "M1 1AA"}, "channel": "letter"}')
) AS e(event_reference, event_timestamp, actor, actor_type, event_data)
CROSS JOIN application a
WHERE a.laa_reference = 'INQ-201-000';

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
WHERE a.laa_reference = 'INQ-201-000';

-- 5. Expect 1 SUBMITTED NIL_BILL claim with 0.00 gross.
SELECT
  c.claim_reference, c.claim_type_id, c.status_id, c.submission_date::date,
  c.total_profit_cost_net, c.total_profit_cost_gross, c.total_profit_cost_vat_zero,
  c.total_funds_remaining_after_claim
FROM claim c
JOIN application a ON a.application_id = c.application_id
WHERE a.laa_reference = 'INQ-201-000';

-- Expect 8 events: 6 for the application and 2 for the claim.
SELECT h.timestamp, h.event_reference, h.actor_type, h.actor, h.event_data
FROM history_event h
JOIN application a ON a.application_id = h.application_id
WHERE a.laa_reference = 'INQ-201-000'
ORDER BY h.timestamp, h.id;

-- Only swap to COMMIT once both result sets look correct.
ROLLBACK;
-- COMMIT;
