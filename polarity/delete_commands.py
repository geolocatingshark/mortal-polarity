# RUN WITH CAUTION
# DELETES ALL PUBLISHED COMMANDS FOR cfg.main_token GLOBALLY
import asyncio

import hikari as h

from . import cfg

rest = h.RESTApp()

TOKEN = cfg.main_token


async def main():
    async with rest.acquire(cfg.main_token, h.TokenType.BOT) as client:
        application = await client.fetch_application()

        await client.set_application_commands(application.id, (), guild=h.UNDEFINED)

        await client.set_application_commands(
            application.id, (), guild=(cfg.kyber_discord_server_id)
        )

        await client.set_application_commands(
            application.id, (), guild=(cfg.control_discord_server_id)
        )


if __name__ == "__main__":
    asyncio.run(main())
