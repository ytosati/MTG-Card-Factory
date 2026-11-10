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
