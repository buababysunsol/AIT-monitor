from __future__ import absolute_import, unicode_literals
from celery import shared_task
import time
import threading
import queue
from network_monitor.network_utils import ping


@shared_task
def add(x, y):
    time.sleep(5)
    print("Task {} + {} = {} Ok!".format(x, y, x + y))
    return x + y


@shared_task
def ping_host(hosts: iter, worker: int = 40):
    class PingWorker(threading.Thread):
        def __init__(self, queue, result):
            super().__init__()
            self.queue = queue
            self.result = result

        def run(self):
            while True:
                ip = self.queue.get()
                r = ping(ip)
                self.result.append({'ip': ip, 'status': r})
                self.queue.task_done()

    result = []
    q = queue.Queue()

    num_worker = min(worker, len(hosts))
    print("Num worker is {}".format(num_worker))

    for _ in range(num_worker):
        w = PingWorker(q, result)
        w.setDaemon(True)
        w.start()

    for host in hosts:
        q.put(str(host))

    q.join()

    return result
