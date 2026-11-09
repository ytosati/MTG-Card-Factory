"""Logging configuration: the application log file and Django's own handlers,
every one of them behind the key redaction filter.
Details: specs/plan.md, section 8 ("Logs").
"""

from logging.handlers import RotatingFileHandler

from core.paths import data_dir

FILE_NAME = "app.log"
# Size-based rotation keeps at most (1 + BACKUP_COUNT) * MAX_BYTES on disk.
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3
# Only the message and standard record fields: `extra` values, which the filter
# does not cover, never reach the file. The formatter appends the exception and the stack.
FILE_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class AppLogHandler(RotatingFileHandler):
    """Rotating file handler that closes the file after each record.

    Windows cannot rename or delete an open file, so holding app.log open would
    block its rotation by another handle and the removal of the home folder.
    """

    def emit(self, record):
        super().emit(record)
        if self.stream is not None:
            self.stream.close()
            self.stream = None


def log_file():
    """`data/logs/app.log` under the application home, with its folder created when missing."""
    folder = data_dir() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / FILE_NAME


def logging_settings():
    """The `LOGGING` setting. Django's default handlers are redefined so each one carries the filter."""
    redaction = ["redact_keys"]
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "redact_keys": {"()": "core.log_redaction.KeyRedactionFilter"},
            "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
        },
        "formatters": {
            "app_file": {"format": FILE_FORMAT},
            "django.server": {
                "()": "django.utils.log.ServerFormatter",
                "format": "[{server_time}] {message}",
                "style": "{",
            },
        },
        "handlers": {
            "app_file": {
                "class": "core.app_log.AppLogHandler",
                "filename": str(log_file()),
                "maxBytes": MAX_BYTES,
                "backupCount": BACKUP_COUNT,
                "encoding": "utf-8",
                "delay": True,
                "formatter": "app_file",
                "filters": redaction,
            },
            # Django's development console and request lines, as in its defaults.
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "filters": ["require_debug_true", *redaction],
            },
            "django.server": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "django.server",
                "filters": redaction,
            },
        },
        "root": {"handlers": ["app_file"], "level": "INFO"},
        "loggers": {
            # Replaces Django's default handlers (console, mail_admins); records still reach app.log through the root.
            "django": {"handlers": ["console"], "level": "INFO"},
            "django.server": {"handlers": ["django.server"], "level": "INFO", "propagate": False},
        },
    }
