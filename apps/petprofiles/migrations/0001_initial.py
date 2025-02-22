# Generated by Django 4.2.6 on 2023-10-28 11:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PetProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pet_id', models.CharField(max_length=255, unique=True)),
                ('pet_name', models.CharField(max_length=255)),
                ('pet_type', models.CharField(choices=[('dog', 'Dog'), ('cat', 'Cat'), ('bird', 'Bird'), ('fish', 'Fish'), ('horse', 'Horse'), ('rabbit', 'Rabbit'), ('turtle', 'Turtle'), ('other', 'Other')], max_length=50)),
                ('birthday', models.DateField(blank=True, null=True)),
                ('profile_picture', models.URLField(blank=True, null=True)),
                ('gender', models.CharField(blank=True, choices=[('m', 'Male'), ('f', 'Female')], max_length=1, null=True)),
                ('bio', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
