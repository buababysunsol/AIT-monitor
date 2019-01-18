import json

import netaddr
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View

from device.models import Device
from discover.forms import AddManualForm, AddDiscoverForm
from .tasks import ping_host


class Discover(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'device.add_device'

    def get(self, request):
        return render(request, "discover/discover.html")

    def post(self, request):
        network_str = request.POST.get('network')
        if not network_str:
            messages.warning(request, 'Network is empty.')
            return redirect('discover-device')

        hosts = []

        if "-" in network_str:
            start_ip, end_ip = network_str.split('-')
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()
            network = netaddr.IPRange(start_ip, end_ip)
            for host in network:
                hosts.append(str(host))
        else:
            try:
                network = netaddr.IPNetwork(network_str)
            except Exception:
                messages.warning(request, 'Network {} is invalid.')
                return redirect('discover-device')

            for host in network.iter_hosts():
                hosts.append(str(host))

        class NetaddrEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, netaddr.IPAddress):
                    return str(o)
                return super().default()

        result = ping_host.apply_async(args=(hosts, 256))
        result_output = result.wait(timeout=None, interval=0.1)

        # Convert to list of object(dict)
        # final_result = []
        # for ip, status in result_output.items():
        #     final_result.append({'ip': ip, 'status': status})

        scan_result = json.dumps(result_output, cls=NetaddrEncoder)
        return render(request, "discover/discover.html", {'add_type': 'discover', 'scan_result': scan_result})


class AddManual(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'device.add_device'

    def post(self, request):
        form = AddManualForm(request.POST)
        if form.is_valid():
            Device.objects.update_or_create(
                ip_address=form.cleaned_data['ip_address'],
                defaults={
                    'snmp_version': form.cleaned_data['snmp_version'],
                    'snmp_username': form.cleaned_data['snmp_username'],
                    'snmp_password': form.cleaned_data['snmp_password'],
                    'snmp_community': form.cleaned_data['snmp_community'],
                    'sitename': form.cleaned_data['sitename']
                }
            )

        messages.success(request, 'Added a device successfully.')
        return redirect('list-device')


class AddDiscover(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'device.add_device'

    def post(self, request):
        form = AddDiscoverForm(request.POST)

        if form.is_valid():
            pre_device = {}
            for name, data in form.cleaned_data.items():
                if name.startswith(('ip_', 'status_')):
                    info, index = name.split('_')
                    device = pre_device.get(index, {})
                    device[info] = data

                    pre_device[index] = device

            for device in pre_device.values():
                ip = device['ip']
                if device['status'] == 'true':
                    status = True
                else:
                    status = False

                Device.objects.update_or_create(
                    ip_address=ip,
                    defaults={
                        'status': status,
                        'snmp_version': form.cleaned_data['snmp_version'],
                        'snmp_community': form.cleaned_data['snmp_community'],
                        'snmp_username': form.cleaned_data['snmp_username'],
                        'snmp_password': form.cleaned_data['snmp_password']
                    }
                )

        messages.success(request, 'Added devices successfully.')
        return redirect('list-device')
