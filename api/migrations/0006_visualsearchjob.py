# Generated by Django 4.2.7 on 2025-06-24 12:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0005_alter_product_barcode'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisualSearchJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('temp_image', models.ImageField(upload_to='temp_searches/')),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('SUCCESS', 'Success'), ('FAILURE', 'Failure')], default='PENDING', max_length=20)),
                ('task_id', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('results', models.JSONField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
