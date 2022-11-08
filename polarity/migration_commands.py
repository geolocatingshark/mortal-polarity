import logging
import hikari as h
import lightbulb
from sqlalchemy import select
import toolbox

from . import cfg, ls, weekly_reset, xur
from .utils import db_session

logger = logging.getLogger(__name__)


@lightbulb.add_checks(lightbulb.checks.has_roles(cfg.admin_role))
@lightbulb.command(
    name="migratability",
    description="Check how many bot follows can be moved to discord follows",
    guilds=(cfg.control_discord_server_id,),
    auto_defer=True,
)
@lightbulb.implements(lightbulb.SlashCommand)
async def migratability(ctx: lightbulb.Context) -> None:
    bot = ctx.bot

    await ctx.respond(content="Working...")

    embed = h.Embed(
        title="Migratability measure",
        description="Proportion of channels migratable to the new follow system\n",
        color=h.Color.from_hex_code("#a96eca"),
    )
    for channel_type, channel_record in [
        ("LS", ls.LostSectorAutopostChannel),
        ("Xur", xur.XurAutopostChannel),
        ("Reset", weekly_reset.WeeklyResetAutopostChannel),
    ]:

        async with db_session() as session:
            async with session.begin():
                channel_id_list = (
                    await session.execute(
                        select(channel_record).where(channel_record.enabled == True)
                    )
                ).fetchall()
                channel_id_list = [] if channel_id_list is None else channel_id_list
                channel_id_list = [channel[0].id for channel in channel_id_list]

        bot_user = bot.get_me()
        no_of_channels = len(channel_id_list)
        no_of_channels_w_perms = 0
        no_of_non_guild_channels = 0
        no_not_found = 0
        for channel_id in channel_id_list:

            try:
                channel = bot.cache.get_guild_channel(
                    channel_id
                ) or await bot.rest.fetch_channel(channel_id)
            except h.errors.NotFoundError:
                no_not_found += 1

            if not isinstance(channel, h.TextableGuildChannel):
                no_of_non_guild_channels += 1
                continue

            server_id = channel.guild_id
            guild: h.Guild = bot.cache.get_guild(
                server_id
            ) or await bot.rest.fetch_guild(server_id)

            bot_member = await bot.rest.fetch_member(guild, bot_user)
            perms = toolbox.calculate_permissions(bot_member, channel)
            logger.info(
                "Guild/Channel : {}/{}".format(channel.get_guild().name, channel.name)
            )

            if h.Permissions.MANAGE_WEBHOOKS in perms:
                no_of_channels_w_perms += 1

        embed.add_field(
            channel_type,
            "({} Migratable + {} Not Applicable + {} Not Found) / {} Total".format(
                no_of_channels_w_perms,
                no_of_non_guild_channels,
                no_not_found,
                no_of_channels,
            ),
            inline=False,
        )

    await ctx.edit_last_response(content="", embed=embed)


def register_all(bot: lightbulb.BotApp) -> None:
    for command in [
        migratability,
    ]:
        bot.command(command)
