import os


def ping(host, times: int = 1):
    for _ in range(times):
        response = os.system("ping -c 1 -W 3 {} > /dev/null".format(host))
        if response == 0:
            return True

    return False
