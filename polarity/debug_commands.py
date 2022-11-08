import logging

import lightbulb

from . import cfg
from .reset_signaller import (
    remote_daily_reset,
    remote_weekend_reset,
    remote_weekly_reset,
)
from .utils import _discord_alert

logger = logging.getLogger(__name__)


@lightbulb.command(
    name="trigger_daily_reset",
    description="Sends a daily reset signal",
    guilds=(cfg.test_env,),
    auto_defer=True,
)
@lightbulb.implements(lightbulb.SlashCommand)
async def daily_reset(ctx: lightbulb.Context) -> None:
    # Move from internal signalling to http signalling for these
    # commands, which makes them a more reliable test
    # ctx.bot.dispatch(autopost.DailyResetSignal(ctx.bot))
    await remote_daily_reset()
    await ctx.respond("Daily reset signal sent")


@lightbulb.command(
    name="trigger_weekly_reset",
    description="Sends a weekly reset signal",
    guilds=(cfg.test_env,),
)
@lightbulb.implements(lightbulb.SlashCommand)
async def weekly_reset(ctx: lightbulb.Context) -> None:
    # Move from internal signalling to http signalling for these
    # commands, which makes them a more reliable test
    # ctx.bot.dispatch(autopost.WeeklyResetSignal(ctx.bot))
    await remote_weekly_reset()
    await ctx.respond("Weekly reset signal sent")


@lightbulb.command(
    name="trigger_weekend_reset",
    description="Sends a weekend reset signal",
    guilds=(cfg.test_env,),
)
@lightbulb.implements(lightbulb.SlashCommand)
async def weekend_reset(ctx: lightbulb.Context) -> None:
    # Move from internal signalling to http signalling for these
    # commands, which makes them a more reliable test
    # ctx.bot.dispatch(autopost.WeekendResetSignal(ctx.bot))
    await remote_weekend_reset()
    await ctx.respond("Weekend reset signal sent")


@lightbulb.option(
    name="text",
    description="Text to alert with",
    type=str,
    default="Testing testing",
)
@lightbulb.command(
    name="test_alert",
    description="Sends a test alert",
    guilds=(cfg.test_env,),
)
@lightbulb.implements(lightbulb.SlashCommand)
async def test_alert(ctx: lightbulb.Context) -> None:
    await _discord_alert(
        ctx.options.text,
        bot=ctx.bot,
        channel=cfg.alerts_channel_id,
        mention_mods=True,
        logger=logger,
    )
    await ctx.respond("Done")


def register_all(bot: lightbulb.BotApp) -> None:
    for command in [
        daily_reset,
        weekly_reset,
        weekend_reset,
        test_alert,
    ]:
        bot.command(command)
