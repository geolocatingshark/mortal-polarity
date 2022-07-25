import hikari
import lightbulb
import uvloop
from lightbulb.ext import tasks

from . import autopost, cfg, controller, debug_commands, ls, user_commands, xur

# Note: Alembic's env.py is set up to import Base from polarity.main
from .utils import Base

uvloop.install()
bot: lightbulb.BotApp = lightbulb.BotApp(**cfg.lightbulb_params)


@tasks.task(m=30, auto_start=True, wait_before_execution=False)
async def autoupdate_status():
    await bot.wait_for(lightbulb.events.LightbulbStartedEvent, timeout=None)
    await bot.update_presence(
        activity=hikari.Activity(
            name="{} servers".format(len(bot.cache.get_guilds_view())),
            type=hikari.ActivityType.LISTENING,
        )
    )


if __name__ == "__main__":
    user_commands.register_all(bot)
    controller.register_all(bot)
    xur.XurControlCommands().register(
        bot, autopost.autopost_cmd_group, controller.kyber
    )
    ls.register(bot, autopost.autopost_cmd_group, controller.kyber)
    autopost.register(bot)
    tasks.load(bot)
    if cfg.test_env:
        debug_commands.register_all(bot)
    bot.run()
