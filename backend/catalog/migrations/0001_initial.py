from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BuildRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('catalog_version', models.PositiveIntegerField()),
                ('started_at', models.DateTimeField()),
                ('finished_at', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='OracleCard',
            fields=[
                ('oracle_id', models.UUIDField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=300)),
                ('mana_cost', models.CharField(blank=True, max_length=100)),
                ('cmc', models.FloatField()),
                ('type_line', models.CharField(max_length=300)),
                ('oracle_text', models.TextField(blank=True)),
                ('colors', models.JSONField(blank=True, default=list)),
                ('color_identity', models.JSONField(blank=True, default=list)),
                ('keywords', models.JSONField(blank=True, default=list)),
                ('power', models.CharField(blank=True, max_length=16, null=True)),
                ('toughness', models.CharField(blank=True, max_length=16, null=True)),
                ('layout', models.CharField(max_length=32)),
                ('faces', models.JSONField(blank=True, default=list)),
                ('commander_legality', models.CharField(choices=[('legal', 'Legal'), ('banned', 'Banned'), ('not_legal', 'Not Legal')], max_length=16)),
                ('game_changer', models.BooleanField(default=False)),
                ('edhrec_rank', models.PositiveIntegerField(blank=True, null=True)),
                ('roles', models.JSONField(blank=True, default=list)),
            ],
        ),
        migrations.CreateModel(
            name='SourceRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('scryfall_oracle', 'Scryfall Oracle')], max_length=32)),
                ('url', models.URLField(max_length=500)),
                ('published_at', models.DateTimeField()),
                ('downloaded_at', models.DateTimeField()),
                ('sha256', models.CharField(max_length=64)),
                ('size', models.BigIntegerField()),
            ],
        ),
    ]
