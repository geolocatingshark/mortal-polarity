from . import cfg
from .autopost import WeeklyResetSignal
from .autopost_url import (
    BaseUrlSignal,
    ControlCommandsImpl,
    UrlAutopostChannel,
    UrlPostSettings,
)
from .utils import Base, week_period


class WeeklyResetPostSettings(UrlPostSettings, Base):
    embed_title: str = "Weekly Reset Post and Infographic"
    embed_description: str = (
        "**From** {start_day_name}, {start_month} {start_day}\n"
        + "**Till** {end_day_name}, {end_month} {end_day}"
    )
    default_gfx_url: str = cfg.defaults.weekly_reset.gfx_url
    default_post_url: str = cfg.defaults.weekly_reset.post_url
    validity_period = staticmethod(week_period)
    embed_command_name = "reset"


class WeeklyResetAutopostChannel(UrlAutopostChannel, Base):
    settings_records = WeeklyResetPostSettings


class WeeklyResetPostSignal(BaseUrlSignal):
    settings_table = WeeklyResetPostSettings
    trigger_on_signal = WeeklyResetSignal


class WeeklyResetPostControlCommands(ControlCommandsImpl):
    announcement_name = "Reset"
    settings_table = WeeklyResetPostSettings
    autopost_channel_table = WeeklyResetAutopostChannel
    autopost_trigger_signal = WeeklyResetPostSignal
    default_gfx_url = cfg.defaults.weekly_reset.gfx_url
    default_post_url = cfg.defaults.weekly_reset.post_url
