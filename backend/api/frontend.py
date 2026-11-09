"""Views that serve the built frontend: the index on every non-API path and `/assets/*`.
Details: specs/plan.md, sections 6 and 9.5.
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_safe

from core.paths import built_asset, built_index

NO_BUILD_MESSAGE = "The built interface was not found. Run npm run build in frontend/ and reload.\n"

# Fixed types: the module system types of Windows come from the registry and can
# be wrong, and a browser refuses a module script served with another type.
FIXED_CONTENT_TYPES = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
}
# A fresh instance holds only the standard table, never the Windows registry.
STANDARD_TYPES = mimetypes.MimeTypes()


def _build_dir():
    # Read on every request so tests can point it at a fixture folder; a rebuild is
    # served without a restart because the files themselves are read per request.
    return Path(settings.FRONTEND_BUILD_DIR)


def _content_type(path):
    fixed = FIXED_CONTENT_TYPES.get(path.suffix.lower())
    if fixed:
        return fixed
    guessed, _encoding = STANDARD_TYPES.guess_type(path.name)
    return guessed or "application/octet-stream"


@require_safe
def index(request, *args, **kwargs):
    """The built `index.html`, sent as built; a short message when no build is present."""
    # A build that cannot be read (access denied included) counts as no build.
    try:
        path = built_index(_build_dir())
        content = path.read_bytes() if path else None
    except OSError:
        content = None
    if content is None:
        return HttpResponse(NO_BUILD_MESSAGE, status=503, content_type="text/plain; charset=utf-8")
    return HttpResponse(content, content_type="text/html; charset=utf-8")


@require_safe
def asset(request, relative=""):
    """A file from `<build>/assets/`; 404 for anything else."""
    path = built_asset(_build_dir(), relative)
    if path is None:
        raise Http404()
    try:
        handle = path.open("rb")
    except OSError:
        raise Http404()
    return FileResponse(handle, content_type=_content_type(path))
