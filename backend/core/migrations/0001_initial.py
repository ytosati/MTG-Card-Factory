import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[('build', 'Build'), ('generate', 'Generate'), ('adjust', 'Adjust'), ('art', 'Art')], max_length=16)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')], default='queued', max_length=16)),
                ('progress', models.FloatField(default=0.0)),
                ('result', models.UUIDField(blank=True, null=True)),
                ('error', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
