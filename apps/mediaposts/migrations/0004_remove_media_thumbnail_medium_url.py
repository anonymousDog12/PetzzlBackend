# Generated by Django 5.0.1 on 2024-01-12 10:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mediaposts', '0003_alter_media_thumbnail_medium_url_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='media',
            name='thumbnail_medium_url',
        ),
    ]
