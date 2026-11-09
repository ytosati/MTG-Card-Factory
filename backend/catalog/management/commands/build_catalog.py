"""`manage.py build_catalog`: builds the reference database in the foreground.
Details: specs/plan.md, section 7 ("All-or-nothing build").
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from catalog.build import run_build
from catalog.selectors import is_ready
from core.errors import INTERNAL_MESSAGE, MappedError

logger = logging.getLogger(__name__)

READY_MESSAGE = "The reference database is ready."
PROGRESS_MESSAGE = "Building the reference database: {percent}%"
ALREADY_READY_MESSAGE = "The reference database is already ready; nothing was downloaded."


class Command(BaseCommand):
    help = "Download the data sources and build the reference database (see spec RN-01, RN-03)."

    def handle(self, *args, **options):
        if is_ready():
            self.stdout.write(self.style.SUCCESS(ALREADY_READY_MESSAGE))
            return
        try:
            run_build(report=_Progress(self.stdout))
        except MappedError as error:
            raise CommandError(error.message) from None
        except Exception:
            # The detail goes only to the redacted log (plan section 6).
            logger.exception("The catalog build failed.")
            raise CommandError(INTERNAL_MESSAGE) from None
        self.stdout.write(self.style.SUCCESS(READY_MESSAGE))


class _Progress:
    """Prints each new whole percentage of the build."""

    def __init__(self, stdout):
        self._stdout = stdout
        self._last = None

    def __call__(self, progress):
        percent = int(progress * 100)
        if percent != self._last:
            self._last = percent
            self._stdout.write(PROGRESS_MESSAGE.format(percent=percent))
