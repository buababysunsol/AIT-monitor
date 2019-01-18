from collections import namedtuple
from datetime import timedelta, datetime

from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from openpyxl import Workbook

from device.models import DeviceInterfaceStatusLog, Device, DeviceStatusHistory, DeviceInterfaceStatusHistory
from network_monitor.utils import diff_datetime_human, timedelta_human


@login_required
@permission_required('device.view_device')
def report(request):
    return render(request, 'report/index.html')


def _get_logs(device_id: int = None, start_time=None, end_time=None):
    """

    :param device_id:
    :param start_time:
    :param end_time:
    :return:
    """
    if device_id:
        device_id = int(device_id)
        logs = DeviceInterfaceStatusLog.objects.filter(device_id=device_id)
    else:
        logs = DeviceInterfaceStatusLog.objects

    if start_time:
        logs = logs.filter(created_at__gte=start_time)
    if end_time:
        logs = logs.filter(created_at__lte=end_time)

    logs = logs.prefetch_related('device').order_by('created_at').all()

    new_log = []
    status_temp = {}

    # Total downtime in seconds
    total_downtime = timedelta(seconds=0)
    total_downtime_new = timedelta(seconds=0)

    ranges = []
    Range = namedtuple('Range', ['start', 'end'])

    for log in logs:
        if log.to_status == 2:
            status_temp[log.description] = {
                'start_at': log.created_at,
                'description': log.description,
                'device': log.device,
                'oid_index': log.oid_index,
            }
        elif log.from_status == 2 and log.to_status == 1:
            if status_temp.get(log.description) is None:
                status_temp[log.description] = {}
                status_temp[log.description]['description'] = log.description
                status_temp[log.description]['device'] = log.device
                status_temp[log.description]['start_at'] = None
                status_temp[log.description]['end_at'] = log.created_at
                status_temp[log.description]['diff'] = None
                status_temp[log.description]['oid_index'] = log.oid_index
                new_log.append(status_temp[log.description])
                del status_temp[log.description]
                continue

            current_log = status_temp[log.description]

            status_temp[log.description]['end_at'] = log.created_at
            status_temp[log.description]['diff'] = diff_datetime_human(status_temp[log.description]['start_at'],
                                                                       log.created_at)

            r1 = Range(start=current_log['start_at'], end=current_log['end_at'])
            ranges.append(r1)
            diff = log.created_at - status_temp[log.description]['start_at']
            total_downtime += diff

            new_log.append(status_temp[log.description])
            del status_temp[log.description]

    ranges.sort(key=lambda x: x.start)
    last_start_downtime = None
    last_end_downtime = None

    for r in ranges:
        if not last_start_downtime:
            total_downtime_new += r.end - r.start
            last_end_downtime = r.end
        else:
            if r.end > last_end_downtime:
                total_downtime_new += (r.end - last_end_downtime)
                last_end_downtime = r.end
        last_start_downtime = r.start

    not_up = []
    for _, log in status_temp.items():
        not_up.append(log)

    new_log = not_up + new_log

    # total_downtime = timedelta_human(total_downtime)
    # total_downtime = timedelta(total_downtime)

    return new_log, total_downtime, total_downtime_new


@login_required
@permission_required('device.view_device')
def report_link(request, device_id=None):
    device_id = request.GET.get('device_id')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')
    export = request.GET.get('export')

    generate_time = timezone.now()

    if device_id:
        device_id = int(device_id)

    logs, total_downtime, total_downtime_new = _get_logs(
        device_id,
        start_time,
        end_time
    )

    devices = Device.objects.all()

    if export == 'excel':
        template_name = 'report/pdf/node_downtime.html'
    elif export == 'pdf':
        template_name = 'report/pdf/link.html'
    else:
        template_name = 'report/link.html'

    return render(request, template_name, {
        'logs': logs, 'new_log': logs, 'devices': devices,
        'start_time': start_time, 'end_time': end_time, 'device_id': device_id,
        'total_downtime': timedelta_human(total_downtime), 'total_downtime_new': timedelta_human(total_downtime_new),
        'generate_time': generate_time
    })


@login_required
@permission_required('device.view_device')
def report_node_updown(request):
    device_id = request.GET.get('device_id')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')
    export = request.GET.get('export')
    status = request.GET.get('status')
    generate_time = timezone.now()

    if start_time:
        start_time = datetime.strptime(start_time, '%Y-%m-%d')
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start_time = generate_time.replace(hour=0, minute=0, second=0, microsecond=0)

    if end_time:
        end_time = datetime.strptime(end_time, '%Y-%m-%d')
        end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        end_time = generate_time.replace(hour=23, minute=59, second=59, microsecond=999999)

    dsh = DeviceStatusHistory.objects.prefetch_related("device").filter(
        created_at__gte=start_time,
        created_at__lte=end_time
    )

    if device_id:
        device_id = int(device_id)
        dsh = dsh.filter(device_id=device_id)

    if status in ("1", "2", "3"):
        dsh = dsh.filter(status=status)

    ranges = []
    total_downtime_new = timedelta(seconds=0)
    Range = namedtuple('Range', ['start', 'end'])

    for item in dsh:
        if item.end_at is None:
            item.end_at = generate_time
        r1 = Range(start=item.start_at, end=item.end_at)
        ranges.append(r1)

    ranges.sort(key=lambda x: x.start)
    last_start_downtime = None
    last_end_downtime = None

    for r in ranges:
        if not last_start_downtime:
            total_downtime_new += r.end - r.start
            last_end_downtime = r.end
        else:
            if r.end > last_end_downtime:
                if r.start > last_end_downtime:
                    start = r.start
                else:
                    start = last_end_downtime
                total_downtime_new += (r.end - start)
                last_end_downtime = r.end
        last_start_downtime = r.start

    total_downtime_new = timedelta_human(total_downtime_new)

    devices = Device.objects.values('ip_address', 'hostname', 'id')

    if export == 'excel':
        template_name = 'report/pdf/node_downtime.html'
    elif export == 'pdf':
        template_name = 'report/pdf/node_downtime.html'
    else:
        template_name = 'report/node_updown.html'

    return render(request, template_name, {
        'items': dsh, 'devices': devices, 'device_id': device_id,
        'start_time': start_time, 'end_time': end_time,
        'generate_time': generate_time, 'total_downtime_new': total_downtime_new,
        'status': status
    })


@login_required
@permission_required('device.view_device')
def export_csv(request):
    header = ['hostname', 'interface', 'description', 'down time', 'up time', 'duration']
    if request.GET.get('device_id'):
        device_id = int(request.GET.get('device_id'))
        device = Device.objects.filter(id=device_id).first()
        title = "Report link for device {} ({})".format(device.hostname, device.ip_address)
    else:
        device_id = None
        title = "Report link for all devices"

    start_time = request.GET.get('start_time')
    if start_time:
        title += " From: {}".format(start_time)
    else:
        title += " From: N/A"

    end_time = request.GET.get('end_time')
    if end_time:
        title += " To: {}".format(end_time)
    else:
        title += " To: N/A"

    logs, total_downtime, total_downtime_new = _get_logs(
        device_id,
        start_time,
        end_time
    )

    dest_filename = 'report-link.xlsx'
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "link"
    ws1.append([title])
    ws1.merge_cells('A1:F1')
    ws1.append(header)

    device_if_cache = {}

    for log in logs:
        if not log.get('start_at'):
            start_at = 'N/A'
        else:
            start_at = log.get('start_at')

        if not log.get('end_at'):
            end_at = 'N/A'
        else:
            end_at = log.get('end_at')

        if not log.get('diff'):
            diff = 'N/A'
        else:
            diff = log.get('diff')

        device_if = device_if_cache.get(log['device'].id)
        if not device_if:
            device_if = device_if_cache[log['device'].id] = {}
            for dif in log['device'].interfaces:
                device_if[dif.oid_index] = dif

        alias = device_if[log['oid_index']].alias

        ws1.append([
            "{}({})".format(log['device'].hostname, log['device'].ip_address),
            log['description'],
            alias,
            start_at,
            end_at,
            diff
        ])

    ws1.append([''])
    ws1.append(['total', '', '', total_downtime])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=' + dest_filename

    wb.save(response)
    return response


@login_required
@permission_required('device.view_device')
def report_link_new(request):
    device_id = request.GET.get('device_id')
    start_at = request.GET.get('start_at')
    end_at = request.GET.get('end_at')
    export = request.GET.get('export')
    status = request.GET.get('status')
    generate_time = timezone.now()

    if device_id:
        device_id = int(device_id)

    if start_at:
        start_at = datetime.strptime(start_at, '%Y-%m-%d')
        start_at = start_at.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start_at = generate_time.replace(hour=0, minute=0, second=0, microsecond=0)

    if end_at:
        end_at = datetime.strptime(end_at, '%Y-%m-%d')
        end_at = end_at.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        end_at = generate_time.replace(hour=23, minute=59, second=59, microsecond=999999)

    interface_history = DeviceInterfaceStatusHistory.objects.prefetch_related("device").filter(
        start_at__gte=start_at,
        start_at__lte=end_at,
    ).order_by('-device', 'start_at')

    if device_id:
        interface_history = interface_history.filter(
            device_id=device_id
        )

    if status in ("1", "2", "3"):
        interface_history = interface_history.filter(status=status)

    devices = Device.objects.values('ip_address', 'hostname', 'id')

    ranges = []
    total_downtime_new = timedelta(seconds=0)
    Range = namedtuple('Range', ['start', 'end'])

    for ih in interface_history:
        if ih.end_at is None:
            ih.end_at = generate_time
        r1 = Range(start=ih.start_at, end=ih.end_at)
        ranges.append(r1)

    ranges.sort(key=lambda x: x.start)
    last_start_downtime = None
    last_end_downtime = None

    for r in ranges:
        if not last_start_downtime:
            total_downtime_new += r.end - r.start
            last_end_downtime = r.end
        else:
            if r.end > last_end_downtime:
                if r.start > last_end_downtime:
                    start = r.start
                else:
                    start = last_end_downtime
                total_downtime_new += (r.end - start)
                last_end_downtime = r.end
        # else:
        #     if r.end > last_end_downtime:
        #         total_downtime_new += (r.end - last_end_downtime)
        #         last_end_downtime = r.end
        last_start_downtime = r.start

    total_downtime_new = timedelta_human(total_downtime_new)

    if export == 'excel':
        template_name = 'report/pdf/node_downtime.html'
    elif export == 'pdf':
        template_name = 'report/pdf/link_new.html'
    else:
        template_name = 'report/link-new.html'
    return render(request, template_name, {
        'interface_history': interface_history,
        'devices': devices,
        'generate_time': generate_time,
        'total_downtime': total_downtime_new,
        'device_id': device_id,
        'start_at': start_at,
        'end_at': end_at,
        'status': status,
    })
