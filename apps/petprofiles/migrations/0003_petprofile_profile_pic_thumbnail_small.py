# Generated by Django 4.2.6 on 2023-10-30 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petprofiles', '0002_rename_profile_picture_petprofile_profile_pic_regular'),
    ]

    operations = [
        migrations.AddField(
            model_name='petprofile',
            name='profile_pic_thumbnail_small',
            field=models.URLField(blank=True, null=True),
        ),
    ]
