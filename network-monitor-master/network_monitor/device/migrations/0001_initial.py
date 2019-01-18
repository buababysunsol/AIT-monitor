# Generated by Django 2.1.2 on 2018-10-16 06:32

import device.models
from django.db import migrations, models
import django.db.models.deletion
import djongo.models.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.CharField(max_length=255, unique=True)),
                ('hostname', models.CharField(blank=True, max_length=255)),
                ('sitename', models.CharField(blank=True, max_length=255)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('uptime', models.IntegerField(default=-1)),
                ('status', models.BooleanField(default=False)),
                ('snmp_version', models.CharField(blank=True, max_length=10)),
                ('snmp_community', models.CharField(blank=True, max_length=255)),
                ('snmp_username', models.CharField(blank=True, max_length=255)),
                ('snmp_password', models.CharField(blank=True, max_length=255)),
                ('ping_status', models.BooleanField(default=False)),
                ('snmp_status', models.BooleanField(default=False)),
                ('interfaces', djongo.models.fields.ArrayModelField(default=[], model_container=device.models.DeviceInterface)),
                ('neighbor', djongo.models.fields.ArrayModelField(default=[], model_container=device.models.Neighbor)),
                ('fans', djongo.models.fields.ArrayModelField(default=[], model_container=device.models.Fans)),
                ('power_supplies', djongo.models.fields.ArrayModelField(default=[], model_container=device.models.PowerSupply)),
                ('temperature', djongo.models.fields.ArrayModelField(default=[], model_container=device.models.Temperature)),
            ],
        ),
        migrations.CreateModel(
            name='DeviceInterfaceStatusLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=255)),
                ('from_status', models.IntegerField(default=0)),
                ('to_status', models.IntegerField(default=0)),
                ('oid_index', models.IntegerField()),
                ('created_at', models.DateTimeField()),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='device.Device')),
            ],
        ),
    ]
