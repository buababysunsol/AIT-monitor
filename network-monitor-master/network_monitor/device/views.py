import datetime
import json
from json import JSONEncoder

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.db.models import Prefetch
from django.forms.models import model_to_dict
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from djongo.models import Model, QuerySet
from django.db.models import Value

from .forms import EditDeviceForm
from .models import Device, DeviceInterfaceStatusLog, DeviceObjectId
from .tasks import fetch_snmp


class DeviceListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'device.change_device'

    def get(self, request):
        devices = Device.objects.all().values('id', 'ip_address', 'sitename', 'hostname', 'snmp_username',
                                              'snmp_password',
                                              'snmp_community', 'snmp_version', 'status', 'ping_status', 'snmp_status')
        devices_json = json.dumps(list(devices))
        return render(request, "device/list_device.html", {'devices': devices_json})

    # This update device information
    def post(self, request):
        devices = Device.objects.filter(snmp_version='v2c')
        update_type = request.POST.get('update_type', 'snmp')
        for device in devices:
            fetch_snmp.delay(device.ip_address, update_type)

        return redirect('list-device')


class EditDeviceView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'device.change_device'

    def post(self, request):
        form = EditDeviceForm(request.POST)
        form.is_valid()
        print(form.errors)
        print(form.cleaned_data)
        if form.is_valid():
            Device.objects.filter(id=form.cleaned_data['id']).update(
                # ip_address=form.cleaned_data['ip_address'],
                snmp_version=form.cleaned_data['snmp_version'],
                snmp_username=form.cleaned_data['snmp_username'],
                snmp_password=form.cleaned_data['snmp_password'],
                snmp_community=form.cleaned_data['snmp_community'],
                sitename=form.cleaned_data['sitename']
            )

        return redirect('list-device')


class SearchDeviceView(PermissionRequiredMixin, View):
    permission_required = 'device.view_device'

    def get(self, request):
        devices = Device.objects.all().values('id', 'ip_address', 'sitename', 'hostname', 'snmp_username',
                                              'snmp_password',
                                              'snmp_community', 'snmp_version', 'status')
        devices_json = json.dumps(list(devices))
        return render(request, 'device/search_device.html', {'devices': devices_json})


@login_required
@permission_required('device.view_device')
def device_view(request, id):
    device = Device.objects.prefetch_related(
        Prefetch('deviceinterfacestatuslog_set', DeviceInterfaceStatusLog.objects.order_by('-created_at')),
        'deviceinterfacestatushistory_set'
    ).get(id=id)
    generate_time = timezone.now()
    return render(request, 'device/view_device.html', {'device': device, 'generate_time': generate_time})


@login_required
@permission_required('device.view_device')
def device_network(request):
    devices = Device.objects.all()
    for device in devices:
        print(device.is_router)

    object_id_cache = {}

    class MyEncoder(JSONEncoder):
        def default(self, o):
            if isinstance(o, QuerySet):
                return list(o)
            if isinstance(o, Model):
                d = model_to_dict(o)
                if isinstance(o, Device):
                    d['is_router'] = o.is_router  # Todo Remove
                    d['is_switch'] = o.is_switch  # Todo Remove
                    if not o.object_id:
                        d['device_type'] = 'Unknown'
                    elif object_id_cache.get(o.object_id[1:]):
                        d['device_type'] = object_id_cache.get(o.object_id[1:])
                    else:
                        obj = DeviceObjectId.objects.filter(object_id=o.object_id[1:]).first()
                        if not obj:
                            object_id_cache[o.object_id[1:]] = 'Unknown'
                        else:
                            object_id_cache[o.object_id[1:]] = obj.device_type
                        d['device_type'] = object_id_cache.get(o.object_id[1:])
                    d['is_down'] = o.is_down()
                return d
            if isinstance(o, datetime.datetime):
                return o.isoformat()
            return super().default(o)

    devices = json.dumps(devices, cls=MyEncoder)
    return render(request, 'device/network.html', {'devices': devices})


@login_required
@permission_required('device.delete_device')
def delete_device(request, id):
    if request.method == 'POST':
        device = Device.objects.get(id=id)
        device.delete()

    return redirect('list-device')
