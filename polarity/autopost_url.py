# Url based autoannounce setup
# Classes must be subclassed and then worked with

import asyncio
import datetime as dt
import functools
import logging
from calendar import month_name as month
from typing import Callable, List, Type
import aiohttp

import hikari as h
import lightbulb as lb
import lightbulb.ext.wtf as wtf
from sqlalchemy import Column, select
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.types import Boolean, DateTime, String

from . import cfg
from .autopost import (
    AutopostsBase,
    BaseChannelRecord,
    BaseCustomEvent,
    BasePostSettings,
)
from .utils import (
    _create_or_get,
    _edit_embedded_message,
    db_session,
    follow_link_single_step,
    operation_timer,
)


logger = logging.getLogger(__name__)


@declarative_mixin
class UrlPostSettings(BasePostSettings):
    # url: the infographic url
    url = Column("url", String, nullable=False)
    # post_url: hyperlink for the post title
    post_url = Column("post_url", String)
    url_redirect_target = Column("url_redirect_target", String)
    url_last_modified = Column("url_last_modified", DateTime)
    url_last_checked = Column("url_last_checked", DateTime)
    # ToDo: Look for all armed url watchers at startup and start them again
    url_watcher_armed = Column(
        "url_watcher_armed", Boolean, default=False, server_default="f"
    )
    default_id: int = 0

    # NOTE These need to be defined for all subclasses:
    embed_title: str
    embed_description: str
    default_gfx_url: str
    default_post_url: str
    # Assign a function to this that returns the validity period of
    # posts made for this announce target
    # Must be a staticmethod decorated function
    validity_period: Callable
    embed_command_name: str
    embed_command_description: str

    def __init__(
        self,
        id: int,
        url: str = None,
        post_url: str = None,
        autoannounce_enabled: bool = True,
    ):
        self.id = id
        self.url = url if url is not None else self.default_gfx_url
        self.post_url = post_url if post_url is not None else self.default_post_url
        self.autoannounce_enabled = autoannounce_enabled

    async def initialise_url_params(self):
        """
        Initialise the Url's redirect_target, last_modified and last_checked properties
        if they are set to None
        """
        if (
            self.url_redirect_target == None
            or self.url_last_checked == None
            or self.url_last_modified == None
        ):
            await self.update_url()

    async def update_url(self):
        redirected_url = await follow_link_single_step(self.url, logger)
        self.url_last_checked = dt.datetime.now()
        if redirected_url != self.url_redirect_target:
            self.url_redirect_target = redirected_url
            self.url_last_modified = self.url_last_checked
        if self.url_last_modified == None:
            self.url_last_modified = self.url_last_checked

    async def wait_for_url_update(self):
        async with db_session() as session:
            async with session.begin():
                session.add(self)
                self.url_watcher_armed = True
            check_interval = 10
            while True:
                try:
                    current_redirected_url = await follow_link_single_step(
                        self.url, logger
                    )
                except aiohttp.ServerDisconnectedError:
                    # Work around rebrandly disconnecting long running
                    # TCP connections that aiohttp maintains for
                    # performance reasons
                    continue
                if current_redirected_url != self.url_redirect_target:
                    async with session.begin():
                        session.add(self)
                        self.url_redirect_target = current_redirected_url
                        self.url_last_modified = dt.datetime.now()
                        self.url_watcher_armed = False
                    return self
                await asyncio.sleep(check_interval)

    async def get_announce_embed(self, date: dt.date = None) -> h.Embed:
        await self.update_url()
        # Use the db date if none is specified
        if date is None:
            date = self.url_last_modified
        # Get the period of validity for this message
        start_date, end_date = self.validity_period(date)
        # Follow urls 1 step into redirects
        gfx_url = self.url_redirect_target
        post_url = self.post_url

        format_dict = {
            "start_month": month[start_date.month],
            "end_month": month[end_date.month],
            "start_day": start_date.day,
            "start_day_name": start_date.strftime("%A"),
            "end_day": end_date.day,
            "end_day_name": end_date.strftime("%A"),
            "post_url": post_url,
            "gfx_url": gfx_url,
        }
        return h.Embed(
            title=self.embed_title.format(**format_dict),
            url=format_dict["post_url"],
            description=self.embed_description.format(**format_dict),
            color=cfg.kyber_pink,
        ).set_image(format_dict["gfx_url"])

    # Note cls is applied partially durign register_embed_user_cmd
    @staticmethod
    async def embed_command_impl(cls, ctx: lb.Context):
        async with db_session() as session:
            async with session.begin():
                settings = await session.get(cls, cls.default_id)
                await ctx.respond(embed=await settings.get_announce_embed())

    @classmethod
    def register_embed_user_cmd(cls, bot: lb.BotApp):
        bot.command(
            wtf.Command[
                wtf.Name[cls.embed_command_name.lower().replace(" ", "_")],
                wtf.Description[
                    cls.embed_command_description
                    or "{} post command".format(cls.embed_command_name)
                ],
                wtf.AutoDefer[True],
                wtf.Implements[lb.SlashCommand],
                wtf.Executes[functools.partial(cls.embed_command_impl, cls)],
            ]
        )


@declarative_mixin
class UrlAutopostChannel(BaseChannelRecord):
    settings_records: Type[UrlPostSettings] = UrlPostSettings


class BaseUrlSignal(BaseCustomEvent):
    """Base class for URL autopost signals

    NOTE these must be specified on subclassing:
    - settings_table: Type[UrlPostSettings]
    - trigger_on_signal: h.Event"""

    settings_table: Type[UrlPostSettings]
    trigger_on_signal: h.Event

    # Whether bot listen has been called on conditional_reset_repeater
    _signal_linked: bool = False

    @classmethod
    async def conditional_reset_repeater(cls, event: h.Event) -> None:
        """When awaited, waits for the settings.wait_for_url_update method to return
        and then fires itself as a signal"""
        if not await cls.is_autoannounce_enabled():
            return

        # Debug code
        if cfg.test_env and cfg.trigger_without_url_update:
            cls.dispatch_with(bot=event.app)

        await cls.wait_for_url_update()
        cls.dispatch_with(bot=event.app)

    @classmethod
    async def is_autoannounce_enabled(cls):
        settings = await _create_or_get(
            cls.settings_table, 0, autoannounce_enabled=True
        )
        return settings.autoannounce_enabled

    @classmethod
    def register(cls, bot: lb.BotApp) -> None:
        self = super().register(bot)
        if not cls._signal_linked:
            bot.listen(self.trigger_on_signal)(self.conditional_reset_repeater)
            cls._signal_linked = True
        return self

    @classmethod
    async def wait_for_url_update(cls) -> None:
        """Waits for the settings.wait_for_url_update() method to return before returning"""
        settings: UrlPostSettings = await _create_or_get(cls.settings_table, 0)
        await settings.wait_for_url_update()


class UrlAutopostsBase(AutopostsBase):
    def __init__(
        self,
        settings_table: Type[UrlPostSettings],
        channel_table: Type[UrlAutopostChannel],
        autopost_trigger_signal: Type[BaseUrlSignal],
        default_gfx_url: str,
        default_post_url: str,
        announcement_name: str,
    ):
        super().__init__()
        self.settings_table = settings_table
        self.autopost_channel_table = channel_table
        self.autopost_trigger_signal = autopost_trigger_signal
        self.default_gfx_url = default_gfx_url
        self.default_post_url = default_post_url
        self.announcement_name = announcement_name

    def register(
        self,
        bot: lb.BotApp,
    ):
        try:
            self.autopost_channel_table.register(
                bot, self.autopost_cmd_group, self.autopost_trigger_signal
            )
            self.settings_table.register_embed_user_cmd(bot)
            self.control_cmd_group.child(self.commands())
            self.autopost_trigger_signal.register(bot)
        except lb.CommandAlreadyExists:
            pass
        finally:
            return self

    def commands(self) -> lb.SlashCommandGroup:
        # Announcement management commands for kyber
        return wtf.Command[
            wtf.Implements[lb.SlashSubGroup],
            wtf.Name[self.announcement_name.lower().replace(" ", "_")],
            wtf.Description[
                "{} announcement management".format(self.announcement_name)
            ],
            wtf.Guilds[cfg.control_discord_server_id],
            wtf.InheritChecks[True],
            wtf.Subcommands[
                # Autoposts Enable/Disable
                wtf.Command[
                    wtf.Name["autoposts"],
                    wtf.Description["Enable or disable automatic announcements"],
                    wtf.AutoDefer[True],
                    wtf.InheritChecks[True],
                    wtf.Options[
                        wtf.Option[
                            wtf.Name["option"],
                            wtf.Description["Enable or disable"],
                            wtf.Type[str],
                            wtf.Choices["Enable", "Disable"],
                            wtf.Required[True],
                        ],
                    ],
                    wtf.Implements[lb.SlashSubCommand],
                    wtf.Executes[self.autopost_ctrl],
                ],
                wtf.Command[
                    wtf.Name["infogfx_url"],
                    wtf.Description[
                        "Set the {} infographic url, to check and post".format(
                            self.announcement_name.lower()
                        )
                    ],
                    wtf.AutoDefer[True],
                    wtf.InheritChecks[True],
                    wtf.Options[
                        wtf.Option[
                            wtf.Name["url"],
                            wtf.Description["The url to set"],
                            wtf.Type[str],
                            wtf.Required[False],
                        ],
                    ],
                    wtf.Implements[lb.SlashSubCommand],
                    wtf.Executes[self.gfx_url],
                ],
                wtf.Command[
                    wtf.Name["post_url"],
                    wtf.Description[
                        "Set the {} post url, to check and post".format(
                            self.announcement_name.lower()
                        )
                    ],
                    wtf.AutoDefer[True],
                    wtf.InheritChecks[True],
                    wtf.Options[
                        wtf.Option[
                            wtf.Name["url"],
                            wtf.Description["The url to set"],
                            wtf.Type[str],
                            wtf.Required[False],
                        ],
                    ],
                    wtf.Implements[lb.SlashSubCommand],
                    wtf.Executes[self.post_url],
                ],
                wtf.Command[
                    wtf.Name["update"],
                    wtf.Description["Update a post"],
                    wtf.AutoDefer[True],
                    wtf.InheritChecks[True],
                    wtf.Implements[lb.SlashSubCommand],
                    wtf.Executes[self.rectify_announcement],
                ],
                wtf.Command[
                    wtf.Name["announce"],
                    wtf.Description["Trigger an announcement manually"],
                    wtf.AutoDefer[True],
                    wtf.InheritChecks[True],
                    wtf.Implements[lb.SlashSubCommand],
                    wtf.Executes[self.manual_announce],
                ],
            ],
        ]

    # Enable or disable autoposts globally
    async def autopost_ctrl(self, ctx: lb.Context):
        option = True if ctx.options.option.lower() == "enable" else False
        async with db_session() as session:
            async with session.begin():
                settings = await session.get(self.settings_table, 0)
                if settings is None:
                    settings = self.settings_table(0, autoannounce_enabled=option)
                    session.add(settings)
                else:
                    settings.autoannounce_enabled = option
        await ctx.respond(
            "Base announcements {}".format("Enabled" if option else "Disabled")
        )

    # Set the gfx url to attach as an image
    async def gfx_url(self, ctx: lb.Context):
        url = ctx.options.url.lower() if ctx.options.url is not None else None
        async with db_session() as session:
            async with session.begin():
                settings: UrlPostSettings = await session.get(self.settings_table, 0)
                if ctx.options.url is None:
                    await ctx.respond(
                        (
                            "The current Base Infographic url is <{}>\n"
                            + "The default Base Infographic url is <{}>"
                        ).format(
                            "unset" if settings is None else settings.url,
                            self.default_gfx_url,
                        )
                    )
                    return
                if settings is None:
                    settings = self.settings_table(0)
                    settings.url = url
                    await settings.initialise_url_params()
                    session.add(settings)
                else:
                    settings.url = url
        await ctx.respond("Base Infographic url updated to <{}>".format(url))

    # Set the post url to link to in the title
    async def post_url(self, ctx: lb.Context):
        url = ctx.options.url.lower() if ctx.options.url is not None else None
        async with db_session() as session:
            async with session.begin():
                settings: UrlPostSettings = await session.get(self.settings_table, 0)
                if ctx.options.url is None:
                    await ctx.respond(
                        (
                            "The current Post url is <{}>\n"
                            + "The default Post url is <{}>"
                        ).format(
                            "unset" if settings is None else settings.post_url,
                            self.default_post_url,
                        )
                    )
                    return
                if settings is None:
                    settings = self.settings_table(0)
                    settings.post_url = url
                    session.add(settings)
                else:
                    settings.post_url = url
        await ctx.respond("Post url updated to <{}>".format(url))

    # Update all current posts
    async def rectify_announcement(self, ctx: lb.Context):
        """Correct a mistake in the announcement,
        pull from urls again and update existing posts"""
        async with db_session() as session:
            async with session.begin():
                settings: UrlPostSettings = await session.get(self.settings_table, 0)
                if settings is None:
                    await ctx.respond("Please enable autoposts before using this cmd")
                else:
                    await settings.update_url()

                channel_record_list = (
                    await session.execute(
                        select(self.autopost_channel_table).where(
                            self.autopost_channel_table.enabled == True
                        )
                    )
                ).fetchall()
                channel_record_list = (
                    [] if channel_record_list is None else channel_record_list
                )
                channel_record_list: List[BaseChannelRecord] = [
                    channel[0] for channel in channel_record_list
                ]
            logger.info("Correcting posts")
            with operation_timer("Announce correction", logger):
                await ctx.respond("Correcting posts now")
                embed = await settings.get_announce_embed()
                no_of_channels = len(channel_record_list)
                percentage_progress = 0
                none_counter = 0
                for idx, channel_record in enumerate(channel_record_list):

                    if channel_record.last_msg_id is None:
                        none_counter += 1
                        continue

                    await _edit_embedded_message(
                        channel_record.last_msg_id,
                        channel_record.id,
                        ctx.bot,
                        embed,
                        logger=logger,
                    )

                    if percentage_progress < round(20 * (idx + 1) / no_of_channels) * 5:
                        percentage_progress = round(20 * (idx + 1) / no_of_channels) * 5
                        await ctx.edit_last_response(
                            "Updating posts: {}%\n".format(percentage_progress)
                        )
                await ctx.edit_last_response(
                    "{} posts corrected".format(no_of_channels - none_counter)
                )

    # Manually trigger an announcement event
    async def manual_announce(self, ctx: lb.Context):
        self.autopost_trigger_signal.dispatch_with(bot=ctx.bot)
        await ctx.respond("Announcements being sent out now")
