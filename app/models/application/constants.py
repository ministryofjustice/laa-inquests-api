"""Application model constants."""

UNGRANTED_SUBSTANTIVE_COST_LIMITATION = 0

# The longest string `date.fromisoformat` accepts ("YYYY-MM-DD"; the week and basic
# forms are shorter), so bounding the request strings here changes nothing it allows.
ISO_DATE_MAX_LENGTH = 10
