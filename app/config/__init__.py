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

    GOV_NOTIFY_API_KEY = os.environ.get("GOV_NOTIFY_API_KEY")
    GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID = os.environ.get(
        "GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID", ""
    )
    GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID = os.environ.get(
        "GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID", ""
    )
    GOV_NOTIFY_CALLBACK_BEARER_TOKEN = os.environ.get(
        "GOV_NOTIFY_CALLBACK_BEARER_TOKEN", ""
    )
    PROVIDER_API_BASE_URL = os.environ.get("PROVIDER_API_BASE_URL", "")
    PROVIDER_API_KEY = os.environ.get("PROVIDER_API_KEY", "")

    SDS_BASE_URL = os.environ.get("SDS_BASE_URL", "")
    SDS_TENANT_ID = os.environ.get("SDS_TENANT_ID", "")
    SDS_CLIENT_ID = os.environ.get("SDS_CLIENT_ID", "")
    SDS_CLIENT_SECRET = os.environ.get("SDS_CLIENT_SECRET", "")
    SDS_SCOPE = os.environ.get("SDS_SCOPE", "")

    INQUESTS_API_TENANT_ID = os.environ.get("INQUESTS_API_TENANT_ID", "")
    INQUESTS_API_CLIENT_ID = os.environ.get("INQUESTS_API_CLIENT_ID", "")
    ENTRA_ALLOWED_SCOPES = os.environ.get(
        "ENTRA_ALLOWED_SCOPES", "User.Provider,User.Caseworker"
    )
