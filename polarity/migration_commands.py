import datetime as dt
import logging

import hikari as h
import lightbulb as lb
import toolbox
from sqlalchemy import select

from . import cfg, ls, weekly_reset, xur
from .utils import FeatureDisabledError, db_session, operation_timer

logger = logging.getLogger(__name__)

embed_color = h.Color.from_hex_code("#a96eca")


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.command(
    name="migratability",
    description="Check how many bot follows can be moved to discord follows",
    guilds=(cfg.control_discord_server_id,),
    auto_defer=True,
)
@lb.implements(lb.SlashCommand)
async def migratability(ctx: lb.Context) -> None:
    bot = ctx.bot

    await ctx.respond(content="Working...")

    embed = h.Embed(
        title="Migratability measure",
        description="Proportion of channels migratable to the new follow system\n",
        color=embed_color,
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
            except (h.errors.NotFoundError, h.errors.ForbiddenError):
                no_not_found += 1
                continue

            if not isinstance(channel, h.TextableGuildChannel):
                no_of_non_guild_channels += 1
                continue

            server_id = channel.guild_id
            guild: h.Guild = bot.cache.get_guild(
                server_id
            ) or await bot.rest.fetch_guild(server_id)

            bot_member = await bot.rest.fetch_member(guild, bot_user)
            perms = toolbox.calculate_permissions(bot_member, channel)

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


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.option("disable_moved", "Disable moved channels", bool, default=False)
@lb.command(
    name="migrate",
    description="Move to the new system",
    guilds=(cfg.control_discord_server_id,),
    auto_defer=True,
)
@lb.implements(lb.SlashCommand)
async def migrate(ctx: lb.Context):
    bot: lb.BotApp = ctx.bot
    disable_moved = ctx.options.disable_moved

    channel_record_list_all_types = []
    async with db_session() as session:
        async with session.begin():
            for follow_channel, channel_table in [
                (cfg.ls_follow_channel_id, ls.LostSectorAutopostChannel),
                (cfg.xur_follow_channel_id, xur.XurAutopostChannel),
                (cfg.reset_follow_channel_id, weekly_reset.WeeklyResetAutopostChannel),
            ]:
                channel_record_list = (
                    await session.execute(
                        select(channel_table).where(channel_table.enabled == True)
                    )
                ).fetchall()
                channel_record_list = (
                    [] if channel_record_list is None else channel_record_list
                )
                channel_record_list = [channel[0] for channel in channel_record_list]
                channel_record_list_all_types.extend(channel_record_list)

            not_found = 0
            forbidden = 0
            bad_request = 0
            not_guild = 0
            misc_exception = 0
            migrated = 0
            iterations = 0

            reporting_embed = (
                h.Embed(
                    title="Follow system migration",
                    description="Operation progress / summary",
                    color=embed_color,
                )
                .add_field(
                    name="Errors",
                    value="{} bad requests\n".format(bad_request)
                    + "{} forbidden\n".format(forbidden)
                    + "{} not found\n".format(not_found)
                    + "{} not in a guild\n".format(not_guild)
                    + "{} misc exception\n".format(misc_exception),
                )
                .add_field(
                    name="Successfully migrated",
                    value="{} successfully migrated\n".format(migrated),
                )
                .add_field(
                    name="Progress",
                    value="{} / {}".format(
                        iterations, len(channel_record_list_all_types)
                    ),
                )
            )
            await ctx.respond(embed=reporting_embed)

            with operation_timer("Migrate") as time_till:
                for channel_record in channel_record_list_all_types:
                    try:
                        channel = bot.cache.get_guild_channel(
                            channel_record.id
                        ) or await bot.rest.fetch_channel(channel_record.id)

                        # Will throw an attribute error if not a guild channel:
                        channel.guild_id

                        if channel_record.server_id == cfg.kyber_discord_server_id:
                            continue

                        if follow_channel < 0:
                            raise FeatureDisabledError(
                                "Following channels is disabled!"
                            )

                        if not follow_channel in [
                            webhook.source_channel.id
                            for webhook in await bot.rest.fetch_channel_webhooks(
                                channel
                            )
                            if isinstance(webhook, h.ChannelFollowerWebhook)
                        ]:
                            await bot.rest.follow_channel(follow_channel, channel)
                            if disable_moved:
                                channel_record.enabled = False
                            session.add(channel_record)
                            migrated += 1
                    except FeatureDisabledError as e:
                        logger.exception(e)
                    except h.BadRequestError:
                        bad_request += 1
                    except h.ForbiddenError:
                        forbidden += 1
                    except h.NotFoundError:
                        not_found += 1
                    except AttributeError:
                        not_guild += 1
                    except Exception as e:
                        logger.exception(e)
                        misc_exception += 1
                    finally:
                        iterations += 1
                        rate = time_till(dt.datetime.now()) / iterations
                        if iterations % round(10 / rate) == 0 or iterations >= len(
                            channel_record_list_all_types
                        ):
                            reporting_embed.edit_field(
                                0,
                                h.UNDEFINED,
                                "{} bad requests\n".format(bad_request)
                                + "{} forbidden\n".format(forbidden)
                                + "{} not found\n".format(not_found)
                                + "{} not in a guild\n".format(not_guild)
                                + "{} misc exception\n".format(misc_exception),
                            ).edit_field(
                                1,
                                h.UNDEFINED,
                                "{} successfully migrated\n".format(migrated),
                            ).edit_field(
                                2,
                                h.UNDEFINED,
                                "{} / {}".format(
                                    iterations, len(channel_record_list_all_types)
                                ),
                            )
                            await ctx.edit_last_response(embed=reporting_embed)
            await session.commit()


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.option("dry_run", "Dry run?", bool, default=True)
@lb.command(
    name="disable_moved",
    description="Remove channels from old system if on new one",
    guilds=(cfg.control_discord_server_id,),
    auto_defer=True,
)
@lb.implements(lb.SlashCommand)
async def disable_moved_channels(ctx: lb.Context):
    bot: lb.BotApp = ctx.bot
    dry_run = ctx.options.dry_run

    channel_record_list_all_types = []
    async with db_session() as session:
        async with session.begin():
            for follow_channel, channel_table in [
                (cfg.ls_follow_channel_id, ls.LostSectorAutopostChannel),
                (cfg.xur_follow_channel_id, xur.XurAutopostChannel),
                (cfg.reset_follow_channel_id, weekly_reset.WeeklyResetAutopostChannel),
            ]:
                channel_record_list = (
                    await session.execute(
                        select(channel_table).where(channel_table.enabled == True)
                    )
                ).fetchall()
                channel_record_list = (
                    [] if channel_record_list is None else channel_record_list
                )
                channel_record_list = [channel[0] for channel in channel_record_list]
                channel_record_list_all_types.extend(channel_record_list)

            disabled = 0
            iterations = 0

            reporting_embed = (
                h.Embed(
                    title="Follow system deduplication",
                    description="Operation progress / summary",
                    color=embed_color,
                )
                .add_field(
                    name="Deduped",
                    value="{} legacy channels disabled\n".format(disabled),
                )
                .add_field(
                    name="Progress",
                    value="{} / {}".format(
                        iterations, len(channel_record_list_all_types)
                    ),
                )
            )
            await ctx.respond(embed=reporting_embed)

            with operation_timer("Migrate") as time_till:
                for channel_record in channel_record_list_all_types:
                    try:
                        channel = bot.cache.get_guild_channel(
                            channel_record.id
                        ) or await bot.rest.fetch_channel(channel_record.id)

                        if channel_record.server_id == cfg.kyber_discord_server_id:
                            continue

                        if follow_channel < 0:
                            raise FeatureDisabledError(
                                "Following channels is disabled!"
                            )

                        if follow_channel in [
                            webhook.source_channel.id
                            for webhook in await bot.rest.fetch_channel_webhooks(
                                channel
                            )
                            if isinstance(webhook, h.ChannelFollowerWebhook)
                        ]:
                            if not dry_run:
                                channel_record.enabled = False
                            session.add(channel_record)
                            disabled += 1
                    except Exception as e:
                        logger.exception(e)
                    finally:
                        iterations += 1
                        rate = time_till(dt.datetime.now()) / iterations
                        if iterations % round(10 / rate) == 0 or iterations >= len(
                            channel_record_list_all_types
                        ):
                            reporting_embed.edit_field(
                                0,
                                h.UNDEFINED,
                                "{} legacy channels disabled\n".format(disabled),
                            ).edit_field(
                                1,
                                h.UNDEFINED,
                                "{} / {}".format(
                                    iterations, len(channel_record_list_all_types)
                                ),
                            )
                            await ctx.edit_last_response(embed=reporting_embed)
                # Commit changes to db after all channels have been iterated through
                await session.commit()


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.command(
    name="restore",
    description="Restore backup ls",
    guilds=(cfg.control_discord_server_id,),
    auto_defer=True,
)
@lb.implements(lb.SlashCommand)
def restore():
    pass


def register_all(bot: lb.BotApp) -> None:
    for command in [
        migratability,
        migrate,
        disable_moved_channels,
    ]:
        bot.command(command)
