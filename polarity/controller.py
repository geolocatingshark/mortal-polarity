import lightbulb
import hikari

from . import cfg


@lightbulb.add_checks(lightbulb.checks.has_roles(cfg.admin_role))
@lightbulb.app_command_permissions(hikari.Permissions.USE_APPLICATION_COMMANDS)
@lightbulb.command(
    "kyber",
    "Commands for Kyber",
    guilds=[
        cfg.kyber_discord_server_id,
    ],
)
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def kyber():
    pass


def register_all(bot: lightbulb.BotApp) -> None:
    bot.command(kyber)
