import lightbulb

from . import autopost, cfg


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
    name="trigger_weekend_reset",
    description="Sends a weekend reset signal",
    guilds=(cfg.test_env,),
)
@lightbulb.implements(lightbulb.SlashCommand)
async def weekend_reset(ctx: lightbulb.Context) -> None:
    ctx.bot.dispatch(autopost.WeekendResetSignal(ctx.bot))
    await ctx.respond("Weekend reset signal sent")


def register_all(bot: lightbulb.BotApp) -> None:
    for command in [daily_reset, weekend_reset]:
        bot.command(command)
