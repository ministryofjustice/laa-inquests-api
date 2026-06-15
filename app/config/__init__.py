import os


class Config(object):
    ENVIRONMENT = os.environ.get("ENV", "unknown")

    # The default DB parameters are set to allow you to connect to the Docker DB
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5436")
    DB_NAME = os.environ.get("DB_NAME", "api")

    DB_LOGGING = os.environ.get("DB_LOGGING", "False") == "True"

    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    SECRET_KEY = os.environ.get("SECRET_KEY", "TEST_KEY")

    # GovNotify Configuration
    GOVNOTIFY_API_KEY = os.environ.get("GOVNOTIFY_API_KEY")
    GOVNOTIFY_TEMPLATE_ID = os.environ.get("GOVNOTIFY_TEMPLATE_ID")
    # TODO: Replace with dynamic provider email when user management is implemented
    GOVNOTIFY_PROVIDER_EMAIL = os.environ.get(
        "GOVNOTIFY_PROVIDER_EMAIL", "provider@example.com"
    )
    FEEDBACK_LINK = os.environ.get(
        "FEEDBACK_LINK", "https://www.gov.uk/government/organisations/legal-aid-agency"
    )

    PROVIDER_API_BASE_URL = os.environ.get("PROVIDER_API_BASE_URL", "")
    PROVIDER_API_KEY = os.environ.get("PROVIDER_API_KEY", "")
