# Generated by Django 2.1.2 on 2018-11-12 02:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('device', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceObjectId',
            fields=[
                ('object_id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('manufacturer', models.CharField(blank=True, max_length=255)),
                ('device_type', models.CharField(max_length=255)),
                ('device_type_name', models.CharField(blank=True, max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='device',
            name='object_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]