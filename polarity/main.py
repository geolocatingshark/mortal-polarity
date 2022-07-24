import hikari
import lightbulb
import uvloop
from lightbulb.ext import tasks

from . import cfg, controller, debug_commands, user_commands, xur, autoannounce

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
    xur.register(bot, autoannounce.autopost_cmd_group, controller.kyber)
    autoannounce.register(bot)
    tasks.load(bot)
    if cfg.test_env:
        debug_commands.register_all(bot)
    bot.run()
