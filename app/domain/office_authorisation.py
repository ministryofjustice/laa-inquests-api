def is_office_authorised(office_id: str, user_office_codes: frozenset[str]) -> bool:
    return office_id in user_office_codes
