import uuid


def create_application_payload() -> dict:
    return {
        "coronersLetterId": str(uuid.uuid4()),
        "proceeding": {"proceedingId": "IQ042"},
        "client": {
            "clientFirstName": "Test",
            "clientLastName": "Surname",
            "dateOfBirth": "1990-01-01",
            "nationalInsuranceNumber": "AB12345A",
            "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
            "correspondenceAddress": {
                "addressLine1": "2 Example Lane",
                "townOrCity": "London",
                "postcode": "SW1A 1AA",
            },
            "hasNoFixedAbode": False,
            "homeAddress": {
                "addressLine1": "1 Example Lane",
                "addressLine2": "Flat 2",
                "townOrCity": "London",
                "county": "Greater London",
                "postcode": "SW1A 1AA",
            },
        },
        "publicBodies": [{"publicBodyId": "Department for Transport"}],
        "deceased": {
            "deceasedFirstName": "Test",
            "deceasedLastName": "Surname",
            "deceasedDateOfBirth": "2000-01-01",
            "deceasedDateOfDeath": "2025-01-01",
            "coronersReference": "COR-2025-001",
            "furtherInformation": "Further details to be confirmed",
            "clientRelationshipToDeceased": "guardian",
        },
        "provider": {
            "officeId": "0U651L",
            "emailAddress": "provider@example.com",
        },
    }


def make_poa_claim_request_body(overrides=None):
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


def make_final_bill_claim_body(overrides=None):
    body = make_poa_claim_request_body(
        {
            "claimType": "FINAL_BILL",
            "poaTypeId": None,
            "totalProfitCostNet": None,
            "totalProfitCostGross": 1200,
            "inquestOutcomes": ["NATURAL_CAUSES"],
            "claimCostTemplateFile": {
                "claimCostTemplateFileId": str(uuid.uuid4()),
                "claimCostTemplateFileName": "final_bill_costs.xlsx",
            },
            "hasCounselBeenPaid": True,
            "hasAlternativeFunding": False,
            "hasRecoveryCostsAwarded": True,
            "financialRecoveryPreviousPreCertificateCosts": 100.00,
            "financialRecoveryCost": 200.00,
            "financialRecoveryDamages": 300.00,
            "financialRecoveryInterest": 50.00,
            "payingParty": "Test Council",
            "numberOfCounselInstructed": "2",
        }
    )
    if overrides is not None:
        body.update(overrides)
    return body


def make_nil_bill_claim_body(overrides=None):
    body = make_poa_claim_request_body(
        {
            "claimType": "NIL_BILL",
            "poaTypeId": None,
            "totalProfitCostNet": None,
            "totalProfitCostGross": 0,
            "inquestOutcomes": ["OPEN_CONCLUSION"],
            "hasAlternativeFunding": False,
            "hasRecoveryCostsAwarded": True,
            "financialRecoveryPreviousPreCertificateCosts": 100.00,
            "financialRecoveryCost": 200.00,
            "financialRecoveryDamages": 300.00,
            "financialRecoveryInterest": 50.00,
            "payingParty": "Test Council",
        }
    )
    del body["claimEvidenceIds"]
    if overrides is not None:
        body.update(overrides)
    return body
