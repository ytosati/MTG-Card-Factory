"""PreToolUse guard for shell commands: blocks secret reads and destructive Git commands."""

import json
import re
import sys

BLOCKED = [
    (re.compile(r"\.env(?!\.example)(?![\w.])"), "reads or writes a .env file (only .env.example is allowed)"),
    (re.compile(r"(^|[\s\"'=])(\./)?data[/\\]"), "touches the data/ folder"),
    (re.compile(r"(^|[\s\"'=])(\./)?runtime[/\\]"), "touches the runtime/ folder"),
    (re.compile(r"\bgit\s+push\b.*(\s--force|\s-f\b|\s\+\S)"), "force-pushes"),
    (re.compile(r"\bgit\s+reset\b.*--hard"), "discards work with git reset --hard"),
    (re.compile(r"\bgit\s+clean\b"), "deletes untracked files with git clean"),
    (re.compile(r"\bRemove-Item\b.*-Recurse", re.IGNORECASE), "deletes folders recursively"),
]


def main() -> int:
    payload = json.load(sys.stdin)
    command = str(payload.get("tool_input", {}).get("command", ""))
    for pattern, reason in BLOCKED:
        if pattern.search(command):
            print(f"Blocked by .claude/hooks/guard_command.py: the command {reason}.", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
