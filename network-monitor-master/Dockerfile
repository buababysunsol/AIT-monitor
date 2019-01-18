FROM python:3.6 AS base

WORKDIR /webapps

RUN apt-get update -y && apt-get install -y software-properties-common \
    && add-apt-repository "deb http://deb.debian.org/debian $(lsb_release -sc) main contrib non-free" \
    && apt-get update && apt-get install -y libsnmp-dev snmp-mibs-downloader

COPY requirements.txt /webapps/requirements.txt
RUN pip install -r requirements.txt
RUN pip install https://github.com/celery/django-celery-beat/zipball/master#egg=django-celery-beat

RUN apt-get remove -y software-properties-common && apt-get clean && rm -rf /var/lib/apt/lists

COPY network_monitor/ /webapps/

FROM base AS celery-worker
ENTRYPOINT ["celery"]
CMD ["-A", "network_monitor", "worker", "-l", "warning", "--concurrency=4"]

FROM base AS celery-beat
ENTRYPOINT ["celery"]
CMD ["-A", "network_monitor", "beat", "-l", "info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]

FROM base AS webapps
ENTRYPOINT ["python", "manage.py"]
CMD ["runserver", "0.0.0.0:8000"]
