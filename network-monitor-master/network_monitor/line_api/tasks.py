import requests
from celery import shared_task
from django.conf import settings

from network_monitor.utils import InterfaceNotifyData
from setting.models import Settings

NOTIFY_URL = "https://notify-api.line.me/api/notify"
NOTIFY_TOKEN = settings.LINE_NOTIFY_TOKEN


def notify_line_interface_status(data: InterfaceNotifyData, token: str = None) -> None:
    """

    :param data: NotifyData
    :param token: Line notify token. You can get here https://notify-bot.line.me
    :return:
    """

    line_notify_message = Settings.objects.filter(key='line_notify_message').first()
    if not line_notify_message:
        return

    message = line_notify_message.value.format(**data._asdict())
    notify.delay(message)


@shared_task
def notify(message: str, token: str = None) -> None:
    if not token:
        token_db = Settings.objects.filter(key='line_notify_token').first()
        if not token_db:
            print("Line notify token not defined in Database.")
            return
        token = token_db.value

    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'Authorization': 'Bearer ' + token
    }

    data = {
        'message': message
    }

    requests.post(NOTIFY_URL, headers=headers, data=data)
