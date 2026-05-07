import asyncio
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import keyring
import yaml
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from ksmonitor.core.alerts import TradeValue

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import Application

    from ksmonitor.core.alerts import BaseAlert

logger = logging.getLogger(__name__)
_DEFAULT_CONFIG_PATH = Path("~").expanduser() / ".ksmonitor" / "config" / "core.yaml"

ALERTS_REGISTRY = {"거래대금": TradeValue}


class TelegramBot:
    def __init__(
        self, alert_register_callback: Callable, alert_unregister_callback: Callable
    ) -> None:
        token = keyring.get_password("ksmonitorTelegramBot", "token")
        if token is None:
            err_msg = "Telegram token not found in credentials manager"
            logger.error(err_msg)
            raise ValueError(err_msg)

        self.alert_register_callback = alert_register_callback
        self.alert_unregister_callback = alert_unregister_callback

        self.application: Application = ApplicationBuilder().token(token).build()
        self.users_per_alert: dict[BaseAlert, set[int]] = defaultdict(set)
        self.alerts_per_user: dict[int, set[BaseAlert]] = defaultdict(set)

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._help(update, context)

    async def _stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        for alert in self.alerts_per_user[chat_id]:
            self.alert_unregister_callback(alert)
            self.users_per_alert[alert].remove(chat_id)

        self.alerts_per_user.pop(chat_id)
        self.save_user_configs()

        await update.message.reply_text("알림이 모두 해지되었습니다.")

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_msg = (
            "명령어: /start, /stop, /help, /alert <alert>, /unalert <alert>, /status"
        )
        await update.message.reply_text(help_msg)

    async def _list_args(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = ["Available alert conditions:"]
        for k in ALERTS_REGISTRY.keys():
            # TODO: add help for each Alert
            message.append(f"\t{k}")

        message = "\n".join(message)
        await context.bot.send_message(update.effective_chat.id, message)

    def _instantiate_alert(self, args: list[str] | None) -> BaseAlert:
        if args is None or len(args) == 0:
            raise IndexError
        else:
            alert_type = args[0]
            alert_args = []
            # Assume alert parameters will only be floats or strings for now.
            # If casting to float fails, argument remains a string
            for a in args[1:]:
                try:
                    alert_args.append(float(a))
                except ValueError:
                    alert_args.append(a)

            # Try instantiating alert with the provided arguments
            # If they don't match Alert parameters, TypeError is raised
            try:
                return ALERTS_REGISTRY[alert_type](*alert_args)
            except KeyError:
                message = f"Unknown Alert type {alert_type}"
                logger.error(message)
                raise KeyError(message) from None
            except TypeError:
                message = f"Mismatch between provided arguments and alert parameters for {alert_type}. (Received {args[1:]})"
                logger.error(message)
                raise TypeError(message) from None

    async def _register_alert(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        args = context.args
        try:
            alert = self._instantiate_alert(args)
            self.alert_register_callback(alert)
            self.users_per_alert[alert].add(update.effective_chat.id)
            self.alerts_per_user[update.effective_chat.id].add(alert)
            self.save_user_configs()

            message = f"알림 등록: {alert.name}"
            await update.message.reply_text(message)

        except IndexError:  # empty args
            # if no arguments provided, guide user to correct format
            await self._list_args(update, context)
        except KeyError as e:
            message = f"{str(e)}는 존재하지 않는 조건입니다."
            await update.message.reply_text(message)
        except TypeError as e:  # argument mismatch
            await update.message.reply_text(str(e))

    async def _unregister_alert(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        args = context.args
        try:
            alert = self._instantiate_alert(args)
            self.alert_unregister_callback(alert)
            self.users_per_alert[alert].discard(update.effective_chat.id)
            self.alerts_per_user[update.effective_chat.id].discard(alert)
            self.save_user_configs()

            message = f"알림 해지: {alert.name}"
            await update.message.reply_text(message)

        except IndexError:  # empty args
            # if no arguments provided, guide user to correct format
            await self._list_args(update, context)
        except KeyError as e:
            message = f"{str(e)}는 존재하지 않는 조건입니다."
            await update.message.reply_text(message)
        except TypeError as e:  # argument mismatch
            await update.message.reply_text(str(e))

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        registered_alerts = self.alerts_per_user[update.effective_chat.id]
        message = [a.name for a in registered_alerts]
        if message:
            message = "Following alerts registered\n" + ", ".join(message)
        else:
            message = "No alerts registered"

        await context.bot.send_message(update.effective_chat.id, message)

    def _setup_bot(self):
        self.application.add_handler(CommandHandler("start", self._start))
        self.application.add_handler(CommandHandler("stop", self._stop))
        self.application.add_handler(CommandHandler("help", self._help))

        self.application.add_handler(CommandHandler("alert", self._register_alert))
        self.application.add_handler(CommandHandler("unalert", self._unregister_alert))
        self.application.add_handler(CommandHandler("status", self._status))

    async def start_bot(self):
        logger.info("Starting Telegram bot")
        self.load_user_configs()
        self._setup_bot()
        async with self.application:
            await self.application.start()
            await self.application.updater.start_polling()
            await asyncio.Event().wait()

    async def notify(self, alert: BaseAlert, message: str) -> None:
        # Telegram API imposes a 4096-character limit;
        #  just cut it off for now -- definitely not a common occurence

        # TODO: split messages at natural breaks; maybe Alerts should return
        #  collections of messages instead even.

        if len(message) > 4096:
            message = message[:4096]

        await asyncio.gather(
            *(
                self.application.bot.send_message(chat_id, message)
                for chat_id in self.users_per_alert[alert]
            )
        )

    def save_user_configs(self, config_path: Path | None = None) -> None:
        """Persist alert subscriptions per chat_id to `core.yaml` so users don't
        have to re-register every time application is restarted.

        Read-modify-write so unrelated top-level keys in `core.yaml` are
        preserved. Atomic via tmp + `os.replace` so a crash mid-write can't
        leave a half-written file.
        """
        path = config_path or _DEFAULT_CONFIG_PATH

        records = []
        for alert, chat_ids in self.users_per_alert.items():
            if not chat_ids:
                continue

            records.append(
                {
                    "type": alert.type_key,
                    "args": list(alert.spec()),
                    "chat_ids": sorted(chat_ids),
                }
            )

        existing: dict = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
        existing["telegram.bot.users_per_alert"] = records

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.safe_dump(existing, f, allow_unicode=True, sort_keys=False)

        os.replace(tmp, path)
        logger.debug(f"Saved {len(records)} alert subscription(s) to `{path}`")

    def load_user_configs(self, config_path: Path | None = None) -> None:
        """Reload alert subscriptions from disk and re-register with the monitor.

        No-op if the config file doesn't exist (first run). Per-record errors
        are logged and skipped so a stale entry can't take the bot down.
        """
        path = config_path or _DEFAULT_CONFIG_PATH
        if not path.exists():
            return

        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        records = cfg.get("telegram.bot.users_per_alert", []) or []
        for record in records:
            try:
                alert = self._instantiate_alert([record["type"], *record["args"]])
            except (KeyError, TypeError) as e:
                logger.warning(f"Skipping unloadable alert record {record!r}: {e}")
                continue

            self.alert_register_callback(alert)
            for chat_id in record.get("chat_ids", []):
                self.users_per_alert[alert].add(chat_id)
                self.alerts_per_user[chat_id].add(alert)

        logger.info(f"Loaded {len(records)} alert subscription(s) from `{path}`")
