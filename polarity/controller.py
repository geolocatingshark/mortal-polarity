import lightbulb as lb

from . import cfg


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.command(
    "kyber",
    "Commands for Kyber",
    guilds=[
        cfg.control_discord_server_id,
    ],
)
@lb.implements(lb.SlashCommandGroup)
async def kyber():
    pass


@kyber.child
@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.command("all_stop", "SHUT DOWN THE BOT", guilds=[cfg.control_discord_server_id])
@lb.implements(lb.SlashSubCommand)
async def all_stop(ctx: lb.Context):
    await ctx.respond("Bot is going down now.")
    await ctx.bot.close()


def register(bot: lb.BotApp) -> None:
    bot.command(kyber)
