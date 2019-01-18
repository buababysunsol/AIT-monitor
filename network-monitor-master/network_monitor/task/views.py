import collections

from django.contrib.auth.decorators import permission_required, login_required
from django.core.cache import cache
from django.shortcuts import render
from django_celery_beat.models import PeriodicTask

from authen.decorators import is_superuser
from network_monitor import celery_app


@is_superuser
def list_task(request):
    celery_hosts = cache.get('celery_hosts')

    # POST = Force clear host cache
    if not celery_hosts or request.method == 'POST':
        celery_hosts = celery_app.control.inspect().ping()
        cache.set('celery_hosts', celery_hosts, 3600)

    active_hosts = []
    for host, result in celery_hosts.items():
        if result.get('ok') == 'pong':
            active_hosts.append(host)

    i = celery_app.control.inspect(active_hosts)

    if i.active():
        active = collections.OrderedDict(sorted(i.active().items()))
    else:
        active = {}

    if i.reserved():
        reserved = collections.OrderedDict(sorted(i.reserved().items()))
    else:
        reserved = {}

    if i.scheduled():
        scheduled = collections.OrderedDict(sorted(i.scheduled().items()))
    else:
        scheduled = {}

    periodic_tasks = PeriodicTask.objects.prefetch_related('interval').all()

    return render(request, 'list_task.html',
                  {'active': active, 'reserved': reserved, 'scheduled': scheduled, 'periodic_tasks': periodic_tasks,
                   'celery_hosts': celery_hosts})
