"""Full-text table over the name, type line and rules text of each card, keyed by oracle_id
(plan sections 4 and 9.1)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE VIRTUAL TABLE oracle_fts USING fts5(oracle_id UNINDEXED, name, type_line, oracle_text)",
            reverse_sql="DROP TABLE oracle_fts",
        ),
    ]
