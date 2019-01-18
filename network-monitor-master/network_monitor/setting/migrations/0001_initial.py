# Generated by Django 2.1.2 on 2018-11-01 02:43

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Settings',
            fields=[
                ('key', models.CharField(max_length=255, primary_key=True, serialize=False, unique=True)),
                ('value', models.CharField(max_length=255, null=True)),
                ('value_date', models.DateTimeField(null=True)),
            ],
        ),
    ]
