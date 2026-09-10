import uuid


def create_application_payload() -> dict:
    return {
        "coronersLetterId": str(uuid.uuid4()),
        "proceeding": {"proceedingId": "IQOT"},
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
