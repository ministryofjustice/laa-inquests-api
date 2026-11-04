import uuid


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
