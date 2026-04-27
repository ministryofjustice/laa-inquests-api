import os

class Config(object):
    ENVIRONMENT = os.environ.get("ENV", "unknown")

    # The default DB parameters are set to allow you to connect to the Docker DB
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", 5436)
    DB_NAME = os.environ.get("DB_NAME", "api")

    DB_LOGGING = os.environ.get("DB_LOGGING", "False") == "True"

    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    SECRET_KEY = os.environ.get("SECRET_KEY", "TEST_KEY")
