from . import cfg
from .autopost import WeeklyResetSignal
from .autopost_url import (
    BaseUrlSignal,
    UrlAutopostsBase,
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
    embed_command_description = "Weekly reset post and infographic"


class WeeklyResetAutopostChannel(UrlAutopostChannel, Base):
    settings_records = WeeklyResetPostSettings
    control_command_name = "reset"
    follow_channel = cfg.reset_follow_channel_id
    autopost_friendly_name = "Weekly reset autoposts"


class WeeklyResetPostSignal(BaseUrlSignal):
    settings_table = WeeklyResetPostSettings
    trigger_on_signal = WeeklyResetSignal


weekly_reset = UrlAutopostsBase(
    settings_table=WeeklyResetPostSettings,
    channel_table=WeeklyResetAutopostChannel,
    autopost_trigger_signal=WeeklyResetPostSignal,
    default_gfx_url=cfg.defaults.weekly_reset.gfx_url,
    default_post_url=cfg.defaults.weekly_reset.post_url,
    announcement_name="Reset",
)
