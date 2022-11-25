import abc
from os import getenv as _getenv

import hikari as h
from sqlalchemy.ext.asyncio import AsyncSession

# Discord API Token
main_token = _getenv("MAIN_TOKEN")
repeater_token = _getenv("MAIN_TOKEN")

# Url for the bot and scheduler db
# SQAlchemy doesn't play well with postgres://, hence we replace
# it with postgresql://
db_url = _getenv("DATABASE_URL")
if db_url.startswith("postgres"):
    repl_till = db_url.find("://")
    db_url = db_url[repl_till:]
    db_url_async = "postgresql+asyncpg" + db_url
    db_url = "postgresql" + db_url

# Async SQLAlchemy DB Session KWArg Parameters
db_session_kwargs = {"expire_on_commit": False, "class_": AsyncSession}

# Debug envs
test_env = _getenv("TEST_ENV") or "false"
test_env = (
    [int(env.strip()) for env in test_env.split(",")] if test_env != "false" else False
)
trigger_without_url_update = _getenv("TRIGGER_WITHOUT_URL_UPDATE") or "false"
trigger_without_url_update = (
    True if trigger_without_url_update.lower() == "true" else False
)

admin_role = int(_getenv("ADMIN_ROLE"))
alerts_channel_id = int(_getenv("ALERTS_CHANNEL_ID"))

kyber_discord_server_id = int(_getenv("KYBER_DISCORD_SERVER_ID"))
control_discord_server_id = int(_getenv("CONTROL_DISCORD_SERVER_ID", default=0))
control_discord_server_id = (
    control_discord_server_id
    if control_discord_server_id != 0
    else kyber_discord_server_id
)

migration_deadline = str(_getenv("MIGRATION_DEADLINE"))
migration_help = str(_getenv("MIGRATION_HELP"))
migration_invite = str(_getenv("MIGRATION_INVITE"))
disable_bad_channels = bool(_getenv("DISABLE_BAD_CHANNELS"))

ls_follow_channel_id = int(_getenv("LS_FOLLOW_CHANNEL_ID"))
xur_follow_channel_id = int(_getenv("XUR_FOLLOW_CHANNEL_ID"))
reset_follow_channel_id = int(_getenv("RESET_FOLLOW_CHANNEL_ID"))

tw_cons_key = str(_getenv("TWITTER_CONSUMER_KEY"))
tw_cons_secret = str(_getenv("TWITTER_CONSUMER_SECRET"))
tw_access_tok = str(_getenv("TWITTER_ACCESS_TOKEN"))
tw_access_tok_secret = str(_getenv("TWITTER_ACCESS_TOKEN_SECRET"))

lightbulb_params = (
    # Only use the test env for testing if it is specified
    {"token": main_token, "default_enabled_guilds": test_env}
    if test_env
    else {"token": main_token}  # Test env isn't specified in production
)

gsheets_credentials = {
    "type": "service_account",
    "project_id": _getenv("SHEETS_PROJECT_ID"),
    "private_key_id": _getenv("SHEETS_PRIVATE_KEY_ID"),
    "private_key": _getenv("SHEETS_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": _getenv("SHEETS_CLIENT_EMAIL"),
    "client_id": _getenv("SHEETS_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": _getenv("SHEETS_CLIENT_X509_CERT_URL"),
}

sheets_ls_url = _getenv("SHEETS_LS_URL")

port = int(_getenv("PORT") or 5000)

kyber_pink = h.Color(0xEC42A5)


class defaults(abc.ABC):
    class xur(abc.ABC):
        gfx_url = "https://kyber3000.com/Xur"
        post_url = "https://kyber3000.com/Xurpost"

    class weekly_reset(abc.ABC):
        gfx_url = "https://kyber3000.com/Reset"
        post_url = "https://kyber3000.com/Resetpost"
