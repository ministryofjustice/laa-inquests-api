import sentry_sdk

from app.config import Config
from app.config.sentry import sentry_config
from app.main import create_app

if Config.SENTRY_DSN:
    sentry_sdk.init(**sentry_config)


api = create_app()
