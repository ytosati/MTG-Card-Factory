"""Read queries of the cards app.
Details: specs/plan.md, sections 5 and 7.
"""

from cards.models import Card, UsageRecord


def get_card(card_id):
    """The card with this id, or None."""
    return Card.objects.filter(pk=card_id).first()


def usage_for(card):
    """The usage records of `card`, oldest first (see spec RN-09)."""
    return UsageRecord.objects.filter(card_id=card.pk).order_by("created_at", "pk")


def card_detail(card_id):
    """The card with this id, its current version and its text usage, or None (see spec RN-26, RN-09)."""
    card = Card.objects.select_related("current_version").filter(pk=card_id).first()
    if card is None:
        return None
    return {"id": card.pk, "current_version": card.current_version, "usage": {"text": usage_for(card)}}
