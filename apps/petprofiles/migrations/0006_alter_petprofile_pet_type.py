# Generated by Django 5.0.1 on 2024-01-22 02:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petprofiles', '0005_alter_petprofile_pet_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='petprofile',
            name='pet_type',
            field=models.CharField(default='dog', editable=False, max_length=50),
        ),
    ]
