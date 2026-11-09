"""The error envelope shared by API answers and stored jobs.
Details: specs/plan.md, section 6.
"""

CODE_INTERNAL = "internal"
INTERNAL_MESSAGE = "Something went wrong in Card Factory. Try again."


def error_body(code, message, setting=None, fields=None):
    """The envelope `{"error": {code, message, setting, fields}}`."""
    return {"error": {"code": code, "message": message, "setting": setting, "fields": fields}}
