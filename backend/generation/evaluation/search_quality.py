"""Manual search quality evaluation: the top ten candidates of twenty requests, marked by a person.

Details: specs/plan.md, section 9.1 (T26 paragraph). Not part of the test
suite. It needs a database built by `python manage.py build_catalog`.

Run from backend/, with the virtual environment active:

    python -m generation.evaluation.search_quality              mark every request not marked yet
    python -m generation.evaluation.search_quality --summary    print the counts and the pass rule
    python -m generation.evaluation.search_quality --request 04-wrath --remark
    python -m generation.evaluation.search_quality --use-provider

By default each request uses the search plan written in requests.json, so the
evaluation measures the search alone and contacts nothing. `--use-provider`
asks the configured text provider for the design call instead (it uses the
key from .env and its tokens are billed). Marks are saved under
data/evaluation/, which is never committed.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUESTS_FILE = Path(__file__).resolve().parent / "requests.json"
TOP = 10
# Plan 9.1: pass when at least 16 of the 20 requests have five or more relevant cards.
RELEVANT_PER_REQUEST = 5
PASSING_REQUESTS = 16


def main(argv=None):
    arguments = _parser().parse_args(argv)
    _setup_django()

    from catalog import selectors
    from core.paths import data_dir

    marks_path = Path(arguments.marks) if arguments.marks else data_dir() / "evaluation" / "search_marks.json"
    requests = _load_requests()
    marks = _load_marks(marks_path)

    if arguments.summary:
        _print_summary(requests, marks)
        return 0
    if not _database_ready(selectors):
        print("The card database is not ready. Build it first: python manage.py build_catalog")
        return 1

    adapter = _provider_adapter() if arguments.use_provider else None
    if arguments.use_provider and adapter is None:
        return 1

    for request in requests:
        if arguments.request and request["id"] != arguments.request:
            continue
        if request["id"] in marks and not arguments.remark and not arguments.print_only:
            continue
        result = _evaluate(request, adapter, interactive=not arguments.print_only)
        if result == "quit":
            break
        if result is not None:
            marks[request["id"]] = result
            _save_marks(marks_path, marks)

    _print_summary(requests, marks)
    return 0


def _database_ready(selectors):
    from django.db import DatabaseError

    # A data folder that was never migrated has no tables at all.
    try:
        return selectors.is_ready()
    except DatabaseError:
        return False


def _parser():
    parser = argparse.ArgumentParser(description="Mark the top ten candidates of each evaluation request.")
    parser.add_argument("--use-provider", action="store_true", help="run the design call with the configured text provider")
    parser.add_argument("--request", help="evaluate only the request with this id")
    parser.add_argument("--remark", action="store_true", help="mark again requests that already have marks")
    parser.add_argument("--print-only", action="store_true", help="print the candidates without asking for marks")
    parser.add_argument("--summary", action="store_true", help="print the counts of the saved marks and exit")
    parser.add_argument("--marks", help="marks file (default: data/evaluation/search_marks.json)")
    return parser


def _setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cardfactory.settings")
    # Type lines carry em dashes; a Windows console may not encode them.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    import django

    django.setup()


def _load_requests():
    return json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))


def _load_marks(path):
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_marks(path, marks):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marks, indent=2), encoding="utf-8")


def _provider_adapter():
    from providers import factory

    result = factory.text_adapter()
    if result.adapter is None:
        print(f"The text provider cannot be used: {result.message}")
        return None
    return result.adapter


def _search_plan(request, adapter):
    """The search plan and candidates: from requests.json, or from the provider's design call."""
    from catalog import selectors

    if adapter is None:
        plan = request["search_plan"]
        filters = {
            "color_identity": request["color_identity"],
            "power_level": request["power_level"],
            "roles": plan["roles"],
            "card_types": plan["card_types"],
            "mana_value_min": plan["mana_value_min"],
            "mana_value_max": plan["mana_value_max"],
        }
        return "hand-written", plan, selectors.search_cards(" ".join(plan["keywords"]), filters)

    from generation.text import plan_card

    step = plan_card(request, adapter)
    print(f"Design intent: {step.design_intent}")
    print(f"Usage: {step.usage.input_tokens} input tokens, {step.usage.output_tokens} output tokens")
    return "provider", step.search_plan, step.candidates


def _evaluate(request, adapter, *, interactive):
    """Show one request's top ten and ask which are relevant; None when skipped, "quit" to stop."""
    from providers.errors import ProviderError

    print()
    print("=" * 78)
    identity = "".join(request["color_identity"]) or "colorless"
    print(f"[{request['id']}] {identity}, {request['power_level']}")
    print(f"Idea: {request['idea']}")
    try:
        source, plan, candidates = _search_plan(request, adapter)
    except ProviderError as error:
        print(f"The design call failed: {error}")
        return None
    print(f"Search plan ({source}): {json.dumps(plan)}")
    top = list(candidates)[:TOP]
    if not top:
        print("No candidates.")
    from catalog import selectors

    # Power and toughness are not part of the search item; they help judge creatures.
    stats = selectors.power_toughness(item["oracle_id"] for item in top)
    for number, item in enumerate(top, start=1):
        print(f"{number:>2}. {item['name']} — {item['mana_cost'] or '(no mana cost)'} — {item['type_line']}")
        # The full text of every face, one line per ability: a cut text cannot be judged.
        text_lines = (item["oracle_text"] or "(no rules text)").split("\n")
        print(f"    Oracle text: {text_lines[0]}")
        for line in text_lines[1:]:
            print(f"                 {line}")
        power, toughness = stats.get(item["oracle_id"], (None, None))
        if power is not None:
            print(f"    power/toughness: {power}/{toughness}")
        print(f"    roles: {', '.join(item['roles']) or '-'}")
        print(f"    identity: {''.join(item['color_identity']) or 'colorless'}")
        print(f"    banned counterexample: {'yes' if item['counterexample'] else 'no'}")
    if not interactive:
        return None

    numbers = _ask_relevant(len(top))
    if numbers in (None, "quit"):
        return numbers
    return {
        "plan_source": source,
        "shown": [item["oracle_id"] for item in top],
        "relevant": [top[number - 1]["oracle_id"] for number in sorted(numbers)],
        "marked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _ask_relevant(count):
    """The set of numbers the person marks as relevant; None to skip, "quit" to stop."""
    while True:
        answer = input("Relevant numbers (such as 1 3 4; empty for none; s to skip; q to quit): ").strip().lower()
        if answer == "q":
            return "quit"
        if answer == "s":
            return None
        parts = answer.replace(",", " ").split()
        if all(part.isdigit() and 1 <= int(part) <= count for part in parts):
            return {int(part) for part in parts}
        print(f"Write numbers from 1 to {count}, separated by spaces.")


def _print_summary(requests, marks):
    print()
    print("Relevant cards in the top ten, per request:")
    marked = 0
    passing = 0
    for request in requests:
        entry = marks.get(request["id"])
        if entry is None:
            print(f"  {request['id']:<24} not marked")
            continue
        marked += 1
        count = len(entry["relevant"])
        passing += count >= RELEVANT_PER_REQUEST
        print(f"  {request['id']:<24} {count:>2} ({entry['plan_source']})")
    print(
        f"Requests with {RELEVANT_PER_REQUEST} or more relevant cards: {passing} of {len(requests)} "
        f"({marked} marked). Pass rule: at least {PASSING_REQUESTS} of {len(requests)}."
    )
    if marked < len(requests):
        print("Result: incomplete; mark every request first.")
    elif passing >= PASSING_REQUESTS:
        print("Result: PASS. Embeddings stay out.")
    else:
        print("Result: FAIL. Record which requests failed and why (plan section 9.1).")


if __name__ == "__main__":
    sys.exit(main())
