"""Services that start API jobs composed from several apps.
Details: specs/plan.md, sections 6 (Jobs) and 7 (Concurrency).
"""

# Modules, not functions, are imported where a test replaces the function.
from core import jobs
from core.errors import MappedError, database_busy_error
from core.models import Job
from generation import text
from providers import factory
from providers.errors import AuthError, ProviderError, message_for

RESULT_CARD = "card"
RESULT_REVISION_FAILURE = "revision_failure"


def start_generation(request):
    """Check the text configuration, then submit the generation as a job (see spec RN-08, RN-50).

    `request` holds `idea`, `color_identity` and `power_level`. A text setting
    to fix raises MappedError with that setting before any provider call; a
    generation already running raises MappedError `generation_running`. Call it
    outside `transaction.atomic()` (see core.jobs.submit).
    """
    adapter = factory.text_adapter()
    if adapter.adapter is None:
        raise MappedError(adapter.code, adapter.message, adapter.setting)
    try:
        return jobs.submit(Job.Kind.GENERATE, lambda report: _run_generation(request))
    except jobs.GenerationRunning as error:
        raise MappedError(error.code, error.message) from error


def _run_generation(request):
    """The job result `{card, revision_failure}`; a provider failure becomes the job's error envelope."""
    try:
        outcome = text.run_generation(request)
    except ProviderError as error:
        # The fixed message of the code, never the provider's text (see spec RN-10).
        # A rejected key names the setting to fix (see spec RN-08).
        setting = "LLM_API_KEY" if isinstance(error, AuthError) else getattr(error, "setting", None)
        raise MappedError(error.code, message_for(error), setting) from error
    except Exception as error:
        busy = database_busy_error(error)
        if busy is None:
            raise
        raise busy from error
    failure = outcome.revision_failure
    return {
        RESULT_CARD: str(outcome.card.pk),
        RESULT_REVISION_FAILURE: None if failure is None else {"code": failure.code, "message": failure.message},
    }
