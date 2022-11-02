import hikari
import lightbulb
import uvloop
from lightbulb.ext import tasks

from . import cfg, controller, debug_commands, user_commands, migration_commands
from .autopost import autoposts
from .ls import lost_sectors

from .weekly_reset import weekly_reset
from .xur import xur

uvloop.install()
bot: lightbulb.BotApp = lightbulb.BotApp(**cfg.lightbulb_params)


@tasks.task(m=30, auto_start=True, wait_before_execution=False)
async def autoupdate_status():
    if not bot.d.has_lightbulb_started:
        await bot.wait_for(lightbulb.events.LightbulbStartedEvent, timeout=None)
        bot.d.has_lightbulb_started = True

    total_users_approx = 0
    for guild in bot.cache.get_guilds_view():
        if isinstance(guild, hikari.Snowflake):
            guild = await bot.rest.fetch_guild(guild)
        total_users_approx += guild.approximate_member_count or 0
    await bot.update_presence(
        activity=hikari.Activity(
            name="{} users : )".format(total_users_approx),
            type=hikari.ActivityType.LISTENING,
        )
    )


if __name__ == "__main__":
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
