import logging

import hikari as h
import lightbulb as lb
import uvloop
from lightbulb.ext import tasks

from . import cfg, controller, debug_commands, migration_commands, user_commands
from .autopost import autoposts
from .ls import lost_sectors
from .weekly_reset import weekly_reset
from .xur import xur

uvloop.install()
bot: lb.BotApp = lb.BotApp(**cfg.lb_params)

logger = logging.getLogger(__name__)


@tasks.task(m=30, auto_start=True, wait_before_execution=False)
async def autoupdate_status():
    if not bot.d.has_lb_started:
        await bot.wait_for(lb.events.LightbulbStartedEvent, timeout=None)
        bot.d.has_lightbulb_started = True

    await bot.update_presence(
        activity=h.Activity(
            name="{} servers : )".format(len(bot.cache.get_guilds_view())),
            type=h.ActivityType.LISTENING,
        )
    )


if __name__ == "__main__":
    logger.info("Listening on port number {}".format(cfg.port))
    autoposts.register(bot)
    controller.register(bot)
    lost_sectors.register(bot)
    user_commands.register(bot)
    weekly_reset.register(bot)
    xur.register(bot)
    tasks.load(bot)
    if cfg.test_env:
        debug_commands.register_all(bot)
    migration_commands.register_all(bot)
    bot.run()
