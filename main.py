import asyncio
import logging
import sys
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


def init():
    import shutil

    configs_path = Path("~").expanduser() / ".ksmonitor" / "configs"
    try:
        configs_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        msg = (
            f"configs directory already exists at {configs_path}. "
            "To re-init, delete the existing directory"
        )
        raise FileExistsError(msg) from None

    if Path("examples").exists():
        shutil.copy(Path("examples") / "core.yaml", configs_path)
        shutil.copy(Path("examples") / "kiwoom.yaml", configs_path)

    print(
        f"Directory created at {configs_path}. "
        f"Make sure to modify the config files to match the usernames in Credential Manager"
    )
    sys.exit()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init()

    filename = Path("~").expanduser() / ".ksmonitor" / "logs" / "ksmonitor.log"
    filename.parent.mkdir(parents=True, exist_ok=True)
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
    client = KiwoomClient(auth, rest_poll_rate=20)
    bot = TelegramBot(
        alert_register_callback=client.register_alerts,
        alert_unregister_callback=client.unregister_alert,
    )

    asyncio.run(start(client, bot))
