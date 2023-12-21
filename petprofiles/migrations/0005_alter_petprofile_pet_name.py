# Generated by Django 4.2.7 on 2023-12-21 03:19

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petprofiles', '0004_remove_petprofile_id_alter_petprofile_pet_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='petprofile',
            name='pet_name',
            field=models.CharField(max_length=50, validators=[django.core.validators.MinLengthValidator(2), django.core.validators.RegexValidator(message='Pet name must be alphanumeric and may include spaces.', regex='^[a-zA-Z0-9 ]+$')]),
        ),
    ]
