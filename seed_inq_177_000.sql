-- Seed application INQ-177-000 (Thomas Riddle, Young Swistak) with four
-- pay-in-full POA claims, a SUBMITTED final bill and their history events, from
-- "Scenario 2 Inquest-reject-Billing test.xlsx".
-- Run via psql through laa-inquest-dev RDS db's port-forward pod and review the
-- dry-run output (w ROLLBACK on the last line) before running with COMMIT.
-- Requires reference data from bin/seed.py (proceeding IQPC, public body HOME_OFFICE).
--
-- Required psql variables: names of files already uploaded through the external UI, i.e.
--   -v evidence_sds_file_name=... -v evidence_file_name=...
--   -v template_sds_file_name=... -v template_file_name=...
\if :{?evidence_sds_file_name}
\else
\echo 'Missing psql variable evidence_sds_file_name'
\quit
\endif
\if :{?evidence_file_name}
\else
\echo 'Missing psql variable evidence_file_name'
\quit
\endif
\if :{?template_sds_file_name}
\else
\echo 'Missing psql variable template_sds_file_name'
\quit
\endif
\if :{?template_file_name}
\else
\echo 'Missing psql variable template_file_name'
\quit
\endif
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
         cl.sds_file_name = 'seed-inq-177-000-coroners-letter'
  INTO v_application_id, v_client_id, v_deceased_id, v_provider_id, v_coroners_letter_id, v_is_seeded
  FROM application a
  LEFT JOIN coroners_letter cl ON cl.coroners_letter_id = a.coroners_letter_id
  WHERE a.laa_reference = 'INQ-177-000';

  IF v_application_id IS NULL THEN
    RETURN;
  END IF;
  IF v_is_seeded IS NOT TRUE THEN
    RAISE EXCEPTION 'Application INQ-177-000 exists but was not created by this script';
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
  VALUES (v_coroners_letter_id, 'seed-inq-177-000-coroners-letter', 'coroners-letter.pdf');

  INSERT INTO address (address_line_1, address_line_2, town_or_city, county, postcode)
  VALUES ('45 Example Road', NULL, 'Chelmsford', 'Essex', 'CM4 12E')
  RETURNING address_id INTO v_correspondence_address_id;

  INSERT INTO address (address_line_1, address_line_2, town_or_city, county, postcode)
  VALUES ('45 Example Road', NULL, 'Chelmsford', 'Essex', 'CM4 12E')
  RETURNING address_id INTO v_home_address_id;

  INSERT INTO client (
    client_first_name, client_last_name, date_of_birth, national_insurance_number,
    has_applied_previously, has_no_fixed_abode, correspondence_address_source,
    correspondence_address_id, home_address_id,
    correspondence_recipient_type, correspondence_recipient_name
  )
  VALUES (
    'Thomas', 'Riddle', '1985-03-15', 'BB654321C',
    false, false, 'USE_SPECIFIED_ADDRESS',
    v_correspondence_address_id, v_home_address_id,
    'PERSON', 'Thomas Riddle'
  )
  RETURNING client_id INTO v_client_id;

  -- The inquest court and its postcode have no dedicated columns, so they are held in coroners_reference.
  INSERT INTO deceased (
    deceased_first_name, deceased_last_name, deceased_date_of_birth, deceased_date_of_death,
    coroners_reference, further_information, client_relationship_to_deceased, client_id
  )
  VALUES (
    'Mary', 'Riddle', '1960-01-01', '2025-05-01',
    'Chelmsford inquest court, CM7 65', 'Further information.', 'Parent', v_client_id
  )
  RETURNING deceased_id INTO v_deceased_id;

  INSERT INTO provider (firm_code, office_id, email_address)
  VALUES ('1473', '0U651L', 'DEBM@DMEEDAN.COM')
  RETURNING provider_id INTO v_provider_id;

  INSERT INTO application (
    laa_reference, created_at, updated_at, status, used_delegated_functions,
    application_type, auto_grant, client_id, deceased_id, provider_id, coroners_letter_id
  )
  VALUES (
    'INQ-177-000', '2025-06-07 09:00:00+00', '2025-06-07 09:00:00+00', 'LIVE', true,
    'INITIAL', true, v_client_id, v_deceased_id, v_provider_id, v_coroners_letter_id
  )
  RETURNING application_id INTO v_application_id;

  INSERT INTO application_proceeding (
    client_involvement_type, merits_decision, application_id, proceeding_id,
    certificate_issue_date, certificate_start_date
  )
  VALUES (
    'RESPONDENT', 'GRANTED', v_application_id, 'IQPC',
    DATE '2025-06-07', DATE '2025-06-07'
  );

  INSERT INTO application_public_body (public_body_id, application_id)
  VALUES ('HOME_OFFICE', v_application_id);
END $$;

-- 2. Edit this list to change the POA claims, ordered by submission date.
-- gross is the claim total (0.00 for a zero VAT-only disbursement); funds_remaining
-- is the 10000 cost limit less the gross of earlier paid claims and this claim.
-- extract_amount: 80% of net + 20% VAT for profit costs; the VAT-zero amount for disbursements.
CREATE TEMP TABLE seed_poa_claims (
  claim_reference text,
  poa_type_id text,
  submission_date timestamptz,
  net numeric(10, 2),
  gross numeric(10, 2),
  vat_zero numeric(10, 2),
  funds_remaining numeric(10, 2),
  extract_amount numeric(10, 2),
  tax_code text
) ON COMMIT DROP;
INSERT INTO seed_poa_claims VALUES
  ('INQC-177A-0001', 'PROFIT_COST', '2026-07-09 09:00:00+00', 75.60, 90.72, NULL, 9909.28, 72.58, 'GB_VAT_20'),
  ('INQC-177A-0002', 'EXPERT_COST', '2026-07-09 10:00:00+00', 0.00, 0.00, 12.00, 9909.28, 12.00, 'ZERO_VAT'),
  ('INQC-177A-0003', 'PROFIT_COST', '2026-07-28 09:00:00+00', 150.54, 180.65, NULL, 9728.63, 144.52, 'GB_VAT_20'),
  ('INQC-177A-0004', 'PROFIT_COST', '2026-07-29 09:00:00+00', 101.25, 121.50, NULL, 9607.13, 97.20, 'GB_VAT_20');

-- 3. POA claims, already PAY_IN_FULL.
INSERT INTO claim (
  application_id, claim_reference, claim_type_id, status_id, submission_date,
  total_profit_cost_net, total_profit_cost_gross, total_profit_cost_vat_zero,
  total_funds_remaining_after_claim, claimant_id, poa_type_id
)
SELECT
  a.application_id, s.claim_reference, 'PAYMENT_ON_ACCOUNT'::claimtype, 'PAY_IN_FULL'::claimstatus,
  s.submission_date, s.net, s.gross, s.vat_zero, s.funds_remaining,
  'debm@dmeedan.com', s.poa_type_id::poatype
FROM seed_poa_claims s
CROSS JOIN application a
WHERE a.laa_reference = 'INQ-177-000';

-- 4. PAY_IN_FULL decision for each POA claim.
INSERT INTO claim_decision (claim_id, decision, created_at)
SELECT c.claim_id, 'PAY_IN_FULL'::claimdecisionstatus, s.submission_date
FROM seed_poa_claims s
JOIN claim c ON c.claim_reference = s.claim_reference;

-- 5. Decision amounts: profit cost claims fill profit_cost_*, disbursements fill disbursement_*.
INSERT INTO claim_decision_amount (
  claim_decision_id, profit_cost_net, profit_cost_gross, profit_cost_vat_zero,
  disbursement_net, disbursement_gross, disbursement_vat_zero
)
SELECT
  cd.claim_decision_id,
  CASE WHEN s.poa_type_id = 'PROFIT_COST' THEN s.net END,
  CASE WHEN s.poa_type_id = 'PROFIT_COST' THEN s.gross END,
  CASE WHEN s.poa_type_id = 'PROFIT_COST' THEN s.vat_zero END,
  CASE WHEN s.poa_type_id <> 'PROFIT_COST' THEN s.net END,
  CASE WHEN s.poa_type_id <> 'PROFIT_COST' THEN s.gross END,
  CASE WHEN s.poa_type_id <> 'PROFIT_COST' THEN s.vat_zero END
FROM seed_poa_claims s
JOIN claim c ON c.claim_reference = s.claim_reference
JOIN claim_decision cd ON cd.claim_id = c.claim_id;

-- 6. Payment extract line for each paid POA claim.
INSERT INTO claim_payment_extract (
  claim_id, sequence_number, invoice_number, invoice_amount, invoice_date,
  invoice_type, tax_code, created_at
)
SELECT
  c.claim_id, 1, s.claim_reference || '_001', s.extract_amount,
  (s.submission_date AT TIME ZONE 'UTC')::date,
  'POA'::invoicetypecode, s.tax_code::taxcode, s.submission_date
FROM seed_poa_claims s
JOIN claim c ON c.claim_reference = s.claim_reference;

-- 7. Final bill, submitted 05/10/2026 and still SUBMITTED. Gross is the sum of the POA claims
-- (90.72 + 12.00 + 180.65 + 121.50); no recovery has been made.
INSERT INTO claim (
  application_id, claim_reference, claim_type_id, status_id, submission_date,
  total_profit_cost_gross, total_funds_remaining_after_claim, claimant_id,
  has_counsel_been_paid, has_alternative_funding, has_recovery_costs_awarded,
  financial_recovery_previous_pre_certificate_costs, financial_recovery_cost,
  financial_recovery_damages, financial_recovery_interest, paying_party,
  number_of_counsel_instructed
)
SELECT
  a.application_id, 'INQC-177A-0005', 'FINAL_BILL'::claimtype, 'SUBMITTED'::claimstatus,
  '2026-10-05 09:00:00+00', 404.87, 9202.26, 'debm@dmeedan.com',
  true, false, false,
  0.00, 0.00, 0.00, 0.00, 'N/A',
  '2'::numberofcounselinstructed
FROM application a
WHERE a.laa_reference = 'INQ-177-000';

INSERT INTO claim_inquest_outcome (claim_id, inquest_outcome_id)
SELECT claim_id, 'ACCIDENT_OR_MISADVENTURE'::inquestoutcomecode
FROM claim
WHERE claim_reference = 'INQC-177A-0005';

-- The cost template is an unlinked claim_evidence row, as created by the UI upload.
WITH template AS (
  INSERT INTO claim_evidence (claim_evidence_id, sds_file_name, file_name, claim_id)
  VALUES (gen_random_uuid(), :'template_sds_file_name', :'template_file_name', NULL)
  RETURNING claim_evidence_id, file_name
)
INSERT INTO claim_cost_template (claim_id, claim_cost_template_file_id, claim_cost_template_file_name)
SELECT c.claim_id, t.claim_evidence_id, t.file_name
FROM claim c
CROSS JOIN template t
WHERE c.claim_reference = 'INQC-177A-0005';

-- 8. Evidence rows for every claim, all pointing at the one uploaded SDS file.
INSERT INTO claim_evidence (claim_evidence_id, sds_file_name, file_name, claim_id)
SELECT gen_random_uuid(), :'evidence_sds_file_name', :'evidence_file_name', c.claim_id
FROM claim c
JOIN application a ON a.application_id = c.application_id
WHERE a.laa_reference = 'INQ-177-000';

-- 9. Application history: submitted, assessed, certificate created, grant email and letter.
INSERT INTO history_event (event_reference, timestamp, actor, actor_type, event_data, application_id)
SELECT
  e.event_reference::historyeventreference, e.event_timestamp::timestamptz, e.actor,
  e.actor_type::actortype, e.event_data::json, a.application_id
FROM (VALUES
  ('APPLICATION_SUBMITTED', '2025-06-07 09:00:00+00', 'DEBM@DMEEDAN.COM', 'PROVIDER', NULL),
  ('APPLICATION_SUBMISSION_CONFIRMATION', '2025-06-07 09:00:05+00', 'System', 'SYSTEM',
    '{"recipient": "DEBM@DMEEDAN.COM", "channel": "email"}'),
  ('APPLICATION_ASSESSMENT_COMPLETED', '2025-06-07 10:00:00+00', 'Seed Caseworker', 'CASEWORKER',
    '{"merits_decision": "Granted"}'),
  ('CERTIFICATE_CREATED', '2025-06-07 10:00:01+00', 'Seed Caseworker', 'CASEWORKER',
    '{"laa_reference": "INQ-177-000"}'),
  ('APPLICATION_GRANTED_EMAIL', '2025-06-07 10:00:02+00', 'System', 'SYSTEM',
    '{"recipient": "DEBM@DMEEDAN.COM", "channel": "email"}'),
  ('APPLICATION_GRANTED_LETTER', '2025-06-07 10:00:03+00', 'System', 'SYSTEM',
    '{"recipient": {"address_line_1": "c/o Thomas Riddle 45 Example Road", "address_line_2": null, "town_or_city": "Chelmsford", "county": "Essex", "postcode": "CM4 12E"}, "channel": "letter"}')
) AS e(event_reference, event_timestamp, actor, actor_type, event_data)
CROSS JOIN application a
WHERE a.laa_reference = 'INQ-177-000';

-- 10. Claim history. Every claim gets submitted + confirmation events; paid POAs also get
-- the auto-approval event and the approval email sent by the follow-up job.
INSERT INTO history_event (event_reference, timestamp, actor, actor_type, event_data, application_id)
SELECT
  e.event_reference::historyeventreference,
  c.submission_date + e.delay,
  CASE WHEN e.actor_type = 'PROVIDER' THEN c.claimant_id ELSE 'System' END,
  e.actor_type::actortype,
  CASE e.event_reference
    WHEN 'CLAIM_SUBMITTED' THEN jsonb_build_object(
      'claim_type', c.claim_type_id::text, 'claim_reference', c.claim_reference)
    WHEN 'CLAIM_SUBMISSION_CONFIRMATION' THEN jsonb_build_object(
      'recipient', p.email_address, 'channel', 'email')
    ELSE jsonb_build_object('claim_reference', c.claim_reference)
  END::json,
  c.application_id
FROM claim c
JOIN application a ON a.application_id = c.application_id
JOIN provider p ON p.provider_id = a.provider_id
CROSS JOIN (VALUES
  ('CLAIM_SUBMITTED', 'PROVIDER', interval '0 seconds'),
  ('CLAIM_SUBMISSION_CONFIRMATION', 'SYSTEM', interval '5 seconds'),
  ('POA_AUTO_APPROVED', 'SYSTEM', interval '10 seconds'),
  ('CLAIM_APPROVED_EMAIL', 'SYSTEM', interval '5 minutes')
) AS e(event_reference, actor_type, delay)
WHERE a.laa_reference = 'INQ-177-000'
  AND (c.claim_type_id = 'PAYMENT_ON_ACCOUNT'
       OR e.event_reference IN ('CLAIM_SUBMITTED', 'CLAIM_SUBMISSION_CONFIRMATION'));

-- 11. Expect 5 claims in submission order: 4 PAY_IN_FULL POAs then 1 SUBMITTED final bill (404.87 gross).
SELECT
  c.claim_reference, c.claim_type_id, c.poa_type_id, c.status_id, c.submission_date::date,
  c.total_profit_cost_net, c.total_profit_cost_gross, c.total_profit_cost_vat_zero,
  c.total_funds_remaining_after_claim
FROM claim c
JOIN application a ON a.application_id = c.application_id
WHERE a.laa_reference = 'INQ-177-000'
ORDER BY c.submission_date, c.claim_reference;

-- Expect 4 extract lines (one per POA claim, 72.58 + 12.00 + 144.52 + 97.20) and none for the final bill.
SELECT c.claim_reference, cpe.invoice_number, cpe.invoice_amount, cpe.invoice_date, cpe.invoice_type, cpe.tax_code
FROM claim_payment_extract cpe
JOIN claim c ON c.claim_id = cpe.claim_id
JOIN application a ON a.application_id = c.application_id
WHERE a.laa_reference = 'INQ-177-000'
ORDER BY c.claim_reference, cpe.sequence_number;

-- Expect 24 events: 6 for the application, 4 per paid POA claim and 2 for the final bill.
SELECT h.timestamp, h.event_reference, h.actor_type, h.actor, h.event_data
FROM history_event h
JOIN application a ON a.application_id = h.application_id
WHERE a.laa_reference = 'INQ-177-000'
ORDER BY h.timestamp, h.id;

-- Only swap to COMMIT once both result sets look correct.
ROLLBACK;
-- COMMIT;
