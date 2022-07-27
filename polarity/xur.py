from . import cfg
from .autopost import WeekendResetSignal
from .autopost_url import (
    BaseUrlSignal,
    ControlCommandsImpl,
    UrlAutopostChannel,
    UrlPostSettings,
)
from .utils import Base, weekend_period


class XurPostSettings(UrlPostSettings, Base):
    embed_title: str = "Xur's Inventory and Location"
    embed_description: str = (
        "**Arrives:** {start_day_name}, {start_month} {start_day}\n"
        + "**Departs:** {end_day_name}, {end_month} {end_day}"
    )
    default_gfx_url: str = cfg.defaults.xur.gfx_url
    default_post_url: str = cfg.defaults.xur.post_url
    validity_period = staticmethod(weekend_period)
    embed_command_name = "Xur"


class XurAutopostChannel(UrlAutopostChannel, Base):
    settings_records = XurPostSettings


class XurSignal(BaseUrlSignal):
    settings_table = XurPostSettings
    trigger_on_signal = WeekendResetSignal


class XurControlCommands(ControlCommandsImpl):
    announcement_name = "Xur"
    settings_table = XurPostSettings
    autopost_channel_table = XurAutopostChannel
    autopost_trigger_signal = XurSignal
    default_gfx_url = cfg.defaults.xur.gfx_url
    default_post_url = cfg.defaults.xur.post_url
