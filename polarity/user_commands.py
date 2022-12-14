# End user facing command implementations for the bot

import asyncio
import logging

import hikari as h
import lightbulb as lb
from sqlalchemy import String
from sqlalchemy.sql.expression import delete, select
from sqlalchemy.sql.schema import Column

from . import cfg, ls
from .autopost import BaseCustomEvent
from .utils import (
    Base,
    db_session,
    follow_link_single_step,
    url_regex,
)

command_registry = {}

logger = logging.getLogger(__name__)


class RefreshCmdListEvent(BaseCustomEvent):
    """Event to trigger a refresh of the user (Kyber) defined commands"""

    def dispatch(self, sync: bool = True):
        # sync: Whether to resync the command list with discord
        self.sync = sync
        return super().dispatch()

    @classmethod
    def dispatch_with(cls, *, bot, sync: bool = True):
        # sync: Whether to resync the command list with discord
        cls.register(bot).dispatch(sync)


class Commands(Base):
    __tablename__ = "commands"
    __mapper_args__ = {"eager_defaults": True}
    name = Column("name", String, primary_key=True)
    description = Column("description", String)
    response = Column("response", String)

    def __init__(self, name, description, response):
        super().__init__()
        self.name = name
        self.description = description
        self.response = response


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.option("response", "Response to post when this command is used", type=str)
@lb.option("description", "Description of what the command posts or does", type=str)
@lb.option("name", "Name of the command to add", type=str)
@lb.command(
    "add",
    "Add a command to the bot",
    auto_defer=True,
    guilds=(cfg.control_discord_server_id,),
)
@lb.implements(lb.SlashCommand)
async def add_command(ctx: lb.Context) -> None:
    name = ctx.options.name.lower()
    description = ctx.options.description
    text = ctx.options.response
    bot = ctx.bot

    async with db_session() as session:
        async with session.begin():
            additional_commands = (await session.execute(select(Commands))).fetchall()
            additional_commands = (
                [] if additional_commands is None else additional_commands
            )
            additional_commands = [command[0].name for command in additional_commands]
            # ToDo: Update hardcoded command names
            if name in ["add", "edit", "delete"] + additional_commands:
                await ctx.respond("A command with that name already exists")
                return

            command = Commands(
                name,
                description,
                text,
            )
            session.add(command)

            command_registry[command.name] = db_command_to_lb_user_command(command)
            bot.command(command_registry[command.name])
            logger.info(command.name + " command registered")
            RefreshCmdListEvent.dispatch_with(bot=bot)

    await ctx.respond("Command added")


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.option(
    "name",
    "Name of the command to delete",
    type=str,
    # Note: This does not work at the start since command_registry
    # isn't populated until the bot starts
    # This is left in in case we modify command_registry in the future
    choices=[cmd for cmd in command_registry.keys()],
)
@lb.command(
    "delete",
    "Delete a command from the bot",
    auto_defer=True,
    guilds=(cfg.control_discord_server_id,),
)
@lb.implements(lb.SlashCommand)
async def del_command(ctx: lb.Context) -> None:
    bot = ctx.bot
    name = ctx.options.name.lower()

    async with db_session() as session:
        try:
            command_to_delete = command_registry.pop(name)
        except KeyError:
            await ctx.respond("No such command found")
        else:
            async with session.begin():
                await session.execute(delete(Commands).where(Commands.name == name))
                bot.remove_command(command_to_delete)
                await ctx.respond("{} command deleted".format(name))
    # Trigger a refresh of the choices in the delete command
    RefreshCmdListEvent.dispatch_with(bot=bot)


@lb.add_checks(lb.checks.has_roles(cfg.admin_role))
@lb.option(
    "new_description",
    "Description of the command to edit",
    type=str,
    default="",
)
@lb.option(
    "new_response",
    "Replace the response field in the command with this",
    type=str,
    default="",
)
@lb.option(
    "new_name",
    "Replace the name of the command with this",
    type=str,
    default="",
)
@lb.option(
    "name",
    "Name of the command to edit",
    type=str,
    # Note: This does not work at the start since command_registry
    # isn't populated until the bot starts
    # This is left in in case we modify command_registry in the future
    choices=[cmd for cmd in command_registry.keys()],
)
@lb.command(
    "edit",
    "Edit a command",
    auto_defer=True,
    guilds=(cfg.control_discord_server_id,),
)
@lb.implements(lb.SlashCommand)
async def edit_command(ctx: lb.Context):
    bot = ctx.bot
    async with db_session() as session:
        async with session.begin():
            command: Commands = (
                await session.execute(
                    select(Commands).where(Commands.name == ctx.options.name.lower())
                )
            ).fetchone()[0]

        if (
            ctx.options.new_name in [None, ""]
            and ctx.options.new_response in [None, ""]
            and ctx.options.new_description in [None, ""]
        ):
            await ctx.respond(
                "The name for this command is currently: {}\n".format(command.name)
                + "The description for this command is currently: {}\n".format(
                    command.description
                )
                + "The response for this command is currently: {}".format(
                    command.response
                )
            )
        else:
            if ctx.options.new_name not in [None, ""]:
                async with session.begin():
                    old_name = command.name
                    new_name = ctx.options.new_name.lower()
                    command.name = new_name
                    session.add(command)
                    # Lightbulb doesn't like changing this:
                    # bot.get_slash_command(ctx.options.name).name = command.name
                    # Need to delete and readd the command instead
                    # -x-x-x-x-
                    # Remove and unregister the old command
                    bot.remove_command(command_registry.pop(old_name))
                    # Register new command with bot and registry dict
                    command_registry[new_name] = db_command_to_lb_user_command(command)
                    bot.command(command_registry[new_name])
            if ctx.options.new_response not in [None, ""]:
                async with session.begin():
                    command.response = ctx.options.new_response
                    session.add(command)
            if ctx.options.new_description not in [None, ""]:
                async with session.begin():
                    command.description = ctx.options.new_description
                    session.add(command)
                    # Lightbulb doesn't like changing this:
                    # bot.get_slash_command(
                    #     ctx.options.name
                    # ).description = command.description
                    # Need to delete and readd the command instead
                    bot.remove_command(command_registry.pop(command.name))
                    command_registry[command.name] = db_command_to_lb_user_command(
                        command
                    )
                    bot.command(command_registry[command.name])

            if ctx.options.new_description not in [
                None,
                "",
            ] or ctx.options.new_name not in [
                None,
                "",
            ]:
                # If either the description or name of a command is changed
                # we will need to have discord update its commands server side
                RefreshCmdListEvent.dispatch_with(bot=bot)

            await ctx.respond("Command updated")


@lb.command("lstoday", "Find out about today's lost sector", auto_defer=True)
@lb.implements(lb.SlashCommand)
async def ls_command(ctx: lb.Context):
    async with db_session() as session:
        async with session.begin():
            settings: ls.LostSectorPostSettings = await session.get(
                ls.LostSectorPostSettings, 0
            )
    embed = await settings.get_announce_embed()
    await ctx.respond(embed=embed)


async def command_options_updater(event: RefreshCmdListEvent):
    choices = [cmd for cmd in command_registry.keys()]
    del_command.options.get("name").choices = choices
    edit_command.options.get("name").choices = choices
    if event.sync:
        await event.app.sync_application_commands()


async def register_commands_on_startup(event: h.StartingEvent):
    """Register additional text commands from db."""
    logger.info("Registering commands")
    async with db_session() as session:
        async with session.begin():
            command_list = (await session.execute(select(Commands))).fetchall()
            command_list = [] if command_list is None else command_list
            command_list = [command[0] for command in command_list]
            for command in command_list:
                command_registry[command.name] = db_command_to_lb_user_command(command)
                event.app.command(command_registry[command.name])
                logger.info(command.name + " registered")

    # Trigger a refresh of the options in the delete command
    # Don't sync since the bot has not started yet and
    # Will sync on its own for startup
    RefreshCmdListEvent.dispatch_with(bot=event.app, sync=False)


async def on_error(event: lb.CommandErrorEvent):
    if isinstance(event.exception, lb.errors.MissingRequiredRole):
        await event.context.respond("Permission denied")
        logger.warning(
            "Note: privlidged command access attempt by uid: {}, name: {}#{}".format(
                event.context.user.id,
                event.context.user.username,
                event.context.user.discriminator,
            )
        )
    else:
        raise event.exception.__cause__ or event.exception


def register(bot: lb.BotApp):
    # Register all commands and listeners with the bot
    for command in [add_command, del_command, edit_command, ls_command]:
        bot.command(command)

    for event, handler in [
        (RefreshCmdListEvent, command_options_updater),
        (h.StartingEvent, register_commands_on_startup),
        (lb.CommandErrorEvent, on_error),
    ]:
        bot.listen(event)(handler)


async def user_command(ctx: lb.Context):
    async with db_session() as session:
        async with session.begin():
            command = (
                await session.execute(
                    select(Commands).where(Commands.name == ctx.command.name)
                )
            ).fetchone()[0]
    text = command.response.strip()
    # Follow redirects once if any
    links = url_regex.findall(text)
    redirected_links = []
    redirected_text = url_regex.sub("{}", text)

    for link in links:
        redirected_links.append(await follow_link_single_step(link, logger))

    redirected_text = redirected_text.format(*redirected_links)

    await ctx.respond(redirected_text)


def db_command_to_lb_user_command(command: Commands):
    # Needs an open db session watching command
    return lb.command(command.name, command.description, auto_defer=True)(
        lb.implements(lb.SlashCommand)(user_command)
    )
