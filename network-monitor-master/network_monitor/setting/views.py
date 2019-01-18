from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect
from django_celery_beat.models import PeriodicTask, PeriodicTasks, IntervalSchedule

from .models import Settings

SETTING_DEFAULT = {
    'email_notify_message': 'Interface: {interface:} on device {hostname:} changed status from {from_status:} to {to_status:}',
    'line_notify_message': 'Interface: {interface:} on device {hostname:} changed status from {from_status:} to {to_status:}',
    'line_node_up_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_down_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_down_notify_header': 'Node {hostname:} ({ip_address:}) [{status:}]',
    'line_node_down_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_up_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_up_notify_header': 'Node {hostname:} ({ip_address:}) [{status:}]',
}

SETTING_DEFAULT = {
    'email_if_updown_notify_header': 'Interface: {interface:} on device {hostname:} changed status from {from_status:} to {to_status:}',
    'email_if_updown_notify_message': 'Interface: {interface:} on device {hostname:} changed status from {from_status:} to {to_status:}',
    'line_notify_message': 'Interface: {interface:} on device {hostname:} changed status from {from_status:} to {to_status:}',
    'line_node_up_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_down_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_down_notify_header': 'Node {hostname:} ({ip_address:}) [{status:}]',
    'line_node_down_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_up_notify_message': 'Node "{hostname:}({ip_address:})" status is "{status:}" \n(Generate on {start_at:})',
    'email_node_up_notify_header': 'Node {hostname:} ({ip_address:}) [{status:}]',
}

@login_required
@permission_required('setting.change_settings')
def index(request):
    if request.method == 'POST':
        return update(request)

    fetch_snmp_task = PeriodicTask.objects.filter(name='fetch-snmp').get()

    settings = {x.key: x.value for x in Settings.objects.all()}
    return render(request, 'setting/index.html', {
        'fetch_snmp_task': fetch_snmp_task,
        'settings': settings
    })


@login_required
@permission_required('setting.change_settings')
def update(request):
    fetch_snmp_interval = request.POST.get('fetch_snmp_interval')
    if fetch_snmp_interval:
        try:
            fetch_snmp_interval = int(fetch_snmp_interval)
            if fetch_snmp_interval <= 0:
                messages.error(request, 'Interval must be greater than 0')
            else:
                fetch_snmp_task = PeriodicTask.objects.filter(name='fetch-snmp').get()
                schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=fetch_snmp_interval,
                    period=IntervalSchedule.SECONDS
                )
                fetch_snmp_task.interval = schedule
                fetch_snmp_task.save()

                PeriodicTasks.changed(fetch_snmp_task)
        except ValueError:
            messages.error(request, 'Interval not a number.')

    ping_test_times = request.POST.get('ping_test_times', 5)
    Settings.objects.update_or_create(
        key='ping_test_times',
        defaults={'value': ping_test_times}
    )

    line_notify_token = request.POST.get('line_notify_token')
    if line_notify_token:
        Settings.objects.update_or_create(
            key='line_notify_token',
            defaults={'value': line_notify_token}
        )

    line_notify_message = request.POST.get('line_notify_message')
    if line_notify_message:
        Settings.objects.update_or_create(
            key='line_notify_message',
            defaults={'value': line_notify_message}
        )

    email_notify_to = request.POST.get('email_notify_to')
    if email_notify_to:
        Settings.objects.update_or_create(
            key='email_notify_to',
            defaults={'value': email_notify_to}
        )

    email_notify_header = request.POST.get('email_notify_header')
    if email_notify_header:
        Settings.objects.update_or_create(
            key='email_notify_header',
            defaults={'value': email_notify_header}
        )

    email_notify_message = request.POST.get('email_notify_message')
    if email_notify_message:
        Settings.objects.update_or_create(
            key='email_notify_message',
            defaults={'value': email_notify_message}
        )

    smtp_email = request.POST.get('smtp_email')
    if smtp_email:
        Settings.objects.update_or_create(
            key='smtp_email',
            defaults={'value': smtp_email}
        )

    smtp_host = request.POST.get('smtp_host')
    if smtp_host:
        Settings.objects.update_or_create(
            key='smtp_host',
            defaults={'value': smtp_host}
        )

    smtp_port = request.POST.get('smtp_port')
    if smtp_port:
        Settings.objects.update_or_create(
            key='smtp_port',
            defaults={'value': smtp_port}
        )

    smtp_username = request.POST.get('smtp_username')
    if smtp_username:
        Settings.objects.update_or_create(
            key='smtp_username',
            defaults={'value': smtp_username}
        )

    smtp_password = request.POST.get('smtp_password')
    if smtp_password and len(smtp_password) > 0:
        Settings.objects.update_or_create(
            key='smtp_password',
            defaults={'value': smtp_password}
        )

    smtp_use_tls = request.POST.get('smtp_use_tls')
    if not smtp_use_tls:
        smtp_use_tls = 'off'
    Settings.objects.update_or_create(
        key='smtp_use_tls',
        defaults={'value': smtp_use_tls}
    )

    smtp_use_ssl = request.POST.get('smtp_use_ssl')
    if not smtp_use_ssl:
        smtp_use_ssl = 'off'
    Settings.objects.update_or_create(
        key='smtp_use_ssl',
        defaults={'value': smtp_use_ssl}
    )

    for key, val in SETTING_DEFAULT.items():
        data = request.POST.get(key)
        if not data:
            data = SETTING_DEFAULT[key]
        Settings.objects.update_or_create(
            key=key,
            defaults={'value': data}
        )

    # node_up_down_email_body = request.POST.get('node_up_down_email_body')
    # if node_up_down_email_body:
    #     Settings.objects.update_or_create(
    #         key='node_up_down_email_body',
    #         defaults={'value': node_up_down_email_body}
    #     )
    #
    # node_up_down_email_header = request.POST.get('node_up_down_email_header')
    # if node_up_down_email_header:
    #     Settings.objects.update_or_create(
    #         key='node_up_down_email_header',
    #         defaults={'value': node_up_down_email_header}
    #     )

    messages.success(request, 'Update settings.')

    return redirect('setting-index')
