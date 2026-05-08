import asyncio
import logging
from pathlib import Path

from ksmonitor.adapters.kiwoom import (
    KiwoomAuth,
    KiwoomClient,
    KiwoomConfig,
)
from ksmonitor.adapters.telegram.bot import TelegramBot


async def dispatch_alerts(client: KiwoomClient, bot: TelegramBot):
    async for alert, event in client.alert_loop():
        await bot.notify(alert, event)


async def start(client: KiwoomClient, bot: TelegramBot):
    await asyncio.gather(
        client.poll_loop(),
        dispatch_alerts(client, bot),
        bot.start_bot(),
    )


if __name__ == "__main__":
    filename = Path("~") / ".ksmonitor" / "logs" / "ksmonitor.log"
    logging.basicConfig(
        filename=filename,
        filemode="w",
        level=logging.INFO,
        format="%(levelname)s:\t%(name)s - %(message)s - %(asctime)s",
        encoding="utf-8",
    )
    logging.getLogger().addHandler(logging.StreamHandler())

    config = KiwoomConfig.from_yaml()
    auth = KiwoomAuth(config)
    client = KiwoomClient(auth, rest_poll_rate=1)
    bot = TelegramBot(
        alert_register_callback=client.register_alerts,
        alert_unregister_callback=client.unregister_alert,
    )

    asyncio.run(start(client, bot))
