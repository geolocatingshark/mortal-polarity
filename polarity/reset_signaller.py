# This architecture for a periodic signal is used since
# apscheduler 3.x has quirks that make it difficult to
# work with in a single process with async without global state.
# These problems are expected to be solved by the release
# of apscheduler 4.x which will have a better async support
# This architecture uses aiohttps requests to a quart (async flask)
# server to send a signal from the scheduler to the reciever.
# The relevant tracking issue for apscheduler 4.x is:
# https://github.com/agronholm/apscheduler/issues/465

import asyncio
import datetime as dt

import aiohttp
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import utc

from . import cfg

# Port for main.py / the "main" process to run on
# This will be 100 less than the Port variable (see Honcho docs)
PORT = cfg.port - 100

# We use the AsyncIOScheduler since the discord client library
# runs mostly asynchronously
# This will be useful when this is run in a single process
# when apscheduler 4.x is released
_scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=cfg.db_url)},
    job_defaults={
        "coalesce": "true",
        "misfire_grace_time": 1800,
        "max_instances": 1,
    },
)


async def remote_daily_reset():
    print("Sending daily reset signal")
    async with aiohttp.ClientSession() as session:
        await session.post(
            "http://127.0.0.1:{}/daily-reset-signal".format(PORT), verify_ssl=False
        )


async def remote_weekly_reset():
    print("Sending weekly reset signal")
    async with aiohttp.ClientSession() as session:
        await session.post(
            "http://127.0.0.1:{}/weekly-reset-signal".format(PORT), verify_ssl=False
        )


async def remote_weekend_reset():
    print("Sending weekend signal")
    async with aiohttp.ClientSession() as session:
        await session.post(
            "http://127.0.0.1:{}/weekend-reset-signal".format(PORT),
            verify_ssl=False,
        )


# This needs to be called at release
def add_remote_announce():
    # (Re)Add the scheduled job that signals destiny 2 reset

    test_time = dt.datetime.now() + dt.timedelta(minutes=2)
    test_cron_dict = {
        "year": test_time.year,
        "month": test_time.month,
        "day": test_time.day,
        "hour": test_time.hour,
        "minute": test_time.minute,
    }

    _scheduler.add_job(
        remote_daily_reset,
        CronTrigger(
            hour=17,
            timezone=utc,
        )
        if not cfg.test_env
        else CronTrigger(**test_cron_dict),
        replace_existing=True,
        id="0",
    )
    _scheduler.add_job(
        remote_weekly_reset,
        CronTrigger(
            day_of_week="tue",
            hour=17,
            timezone=utc,
        )
        if not cfg.test_env
        else CronTrigger(**test_cron_dict),
        replace_existing=True,
        id="1",
    )
    _scheduler.add_job(
        remote_weekend_reset,
        CronTrigger(
            day_of_week="fri",
            hour=17,
            timezone=utc,
        )
        if not cfg.test_env
        else CronTrigger(**test_cron_dict),
        replace_existing=True,
        id="2",
    )

    # Start up then shut down the scheduler to commit changes to the DB
    _scheduler.start(paused=True)
    _scheduler.shutdown(wait=True)


def start():
    """Blocking function to start the scheduler"""
    _scheduler.start()
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    start()
