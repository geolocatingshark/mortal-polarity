import lightbulb

from . import autopost, cfg
from .utils import _discord_alert


@lightbulb.command(
    name="trigger_daily_reset",
    description="Sends a daily reset signal",
    guilds=(cfg.test_env,),
)
@lightbulb.implements(lightbulb.SlashCommand)
async def daily_reset(ctx: lightbulb.Context) -> None:
    ctx.bot.dispatch(autopost.DailyResetSignal(ctx.bot))
    await ctx.respond("Daily reset signal sent")


@lightbulb.command(
    name="trigger_weekly_reset",
    description="Sends a weekly reset signal",
    guilds=(cfg.test_env,),
)
@lightbulb.implements(lightbulb.SlashCommand)
async def weekly_reset(ctx: lightbulb.Context) -> None:
    ctx.bot.dispatch(autopost.WeeklyResetSignal(ctx.bot))
    await ctx.respond("Weekly reset signal sent")


@lightbulb.command(
    name="trigger_weekend_reset",
    description="Sends a weekend reset signal",
    guilds=(cfg.test_env,),
)
@lightbulb.implements(lightbulb.SlashCommand)
async def weekend_reset(ctx: lightbulb.Context) -> None:
    ctx.bot.dispatch(autopost.WeekendResetSignal(ctx.bot))
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
