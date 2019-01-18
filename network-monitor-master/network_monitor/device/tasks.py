# Create your tasks here
from __future__ import absolute_import, unicode_literals

from typing import List

from celery import group, shared_task
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.utils import timezone
from easysnmp import Session, EasySNMPTimeoutError, SNMPVariable

from line_api.tasks import notify_line_interface_status, notify as line_notify
from network_monitor.network_utils import ping
from network_monitor.utils import InterfaceNotifyData
from setting.models import Settings
from setting.views import SETTING_DEFAULT
from .models import Device, DeviceInterface, Neighbor, DeviceInterfaceStatusLog, Fans, PowerSupply, Temperature, \
    Hardware, DeviceStatusHistory, CpuHistory, DeviceInterfaceStatusHistory

now = timezone.now()


def fetch_basic_info(session, device):
    sys_oids = [
        '1.3.6.1.2.1.1.5.0',  # sysName
        '1.3.6.1.2.1.1.1.0',  # sysDescr
        '1.3.6.1.2.1.1.3.0',  # sysUptime
        # '1.3.6.1.2.1.1.2.0',  # sysObjectId
    ]

    sys_info = session.get(sys_oids)
    hostname = sys_info[0]
    desc = sys_info[1]
    uptime = sys_info[2]
    # object_id = sys_info[3]

    device.hostname = hostname.value
    device.description = desc.value
    device.uptime = int(uptime.value)
    # device.object_id = object_id.value

    # sysObjectId
    session.use_numeric = False
    info = session.get(['1.3.6.1.2.1.1.2.0'])
    device.object_id = info[0].value
    session.use_numeric = True

    # Get management IP Subnet mask
    # http://cric.grenoble.cnrs.fr/Administrateurs/Outils/MIBS/?oid=1.3.6.1.2.1.4.20.1.3
    oid = '1.3.6.1.2.1.4.20.1.3.' + device.ip_address  # ipAdEntNetMask
    netmask: SNMPVariable = session.get(oid)
    if netmask:
        device.netmask = netmask.value
    else:
        device.netmask = None

    return True


def fetch_hardware_info(session, device):
    # More info: http://www.oidview.com/mibs/9/CISCO-ENVMON-MIB.html

    env_oids = [
        '1.3.6.1.4.1.9.9.13.1.3.1.2',  # ciscoEnvMonTemperatureStatusDescr
        '1.3.6.1.4.1.9.9.13.1.3.1.3',  # ciscoEnvMonTemperatureStatusValue
        '1.3.6.1.4.1.9.9.13.1.3.1.4',  # ciscoEnvMonTemperatureThreshold
        '1.3.6.1.4.1.9.9.13.1.3.1.6',  # ciscoEnvMonTemperatureState
        '1.3.6.1.4.1.9.9.13.1.4.1.2',  # ciscoEnvMonFanStatusDescr
        '1.3.6.1.4.1.9.9.13.1.4.1.3',  # ciscoEnvMonFanState
        '1.3.6.1.4.1.9.9.13.1.5.1.2',  # ciscoEnvMonSupplyStatusDescr
        '1.3.6.1.4.1.9.9.13.1.5.1.3'  # ciscoEnvMonSupplyState
    ]

    env_info = session.bulkwalk(env_oids)

    temperature = {}
    fans = {}
    power_supplies = {}

    for item in env_info:

        if item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.3.1.2'):
            oid_index = item.oid_index
            tempera = temperature.setdefault(oid_index, Temperature())
            tempera.description = item.value
        elif item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.3.1.3'):
            oid_index = item.oid_index
            tempera = temperature.setdefault(oid_index, Temperature())
            tempera.value = int(item.value)
        elif item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.3.1.4'):
            oid_index = item.oid_index
            tempera = temperature.setdefault(oid_index, Temperature())
            tempera.threshold = int(item.value)
        elif item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.3.1.6'):
            oid_index = item.oid_index
            tempera = temperature.setdefault(oid_index, Temperature())
            tempera.state = int(item.value)
        elif item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.4.1.2'):
            oid_index = item.oid_index
            fan = fans.setdefault(oid_index, Fans())
            fan.description = item.value
        elif item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.4.1.3'):
            oid_index = item.oid_index
            fan = fans.setdefault(oid_index, Fans())
            fan.state = int(item.value)
        elif item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.5.1.2'):
            oid_index = item.oid_index
            psu = power_supplies.setdefault(oid_index, PowerSupply())
            psu.description = item.value
        elif item.oid.startswith('.1.3.6.1.4.1.9.9.13.1.5.1.3'):
            oid_index = item.oid_index
            psu = power_supplies.setdefault(oid_index, PowerSupply())
            psu.state = int(item.value)

    device.fans = list(fans.values())
    device.power_supplies = list(power_supplies.values())
    device.temperature = list(temperature.values())

    return True


def fetch_hardware_info_2(session, device):
    # https://community.cisco.com/t5/network-management/snmp-monitor-for-temperature-status/td-p/2011008
    oids = [
        '1.3.6.1.2.1.47.1.1.1.1.2',  # entPhysicalDescr
        '1.3.6.1.4.1.9.9.91.1.2.1.1.4',  # entSensorThresholdValue
        '1.3.6.1.4.1.9.9.91.1.1.1.1.4',  # entSensorValue
        '1.3.6.1.4.1.9.9.91.1.1.1.1.5',  # entSensorStatus
    ]

    hardware_items = {}

    # Get name
    items = session.bulkwalk(oids[0])
    for item in items:
        # oid_index = item.oid.split('.')[-1]
        # print(item.oid.split('.'), item.oid_index)
        oid_index = item.oid_index
        hardware_obj = Hardware()
        hardware_obj.description = item.value
        hardware_items[oid_index] = hardware_obj

    # entSensorThresholdValue
    items = session.bulkwalk(oids[1])
    for item in items:
        oid_index = item.oid.split('.')[-1]
        hardware_obj = hardware_items.get(oid_index)
        if not hardware_obj:
            continue
        hardware_obj.threshold = item.value

    # entSensorValue
    items = session.bulkwalk(oids[2])
    for item in items:
        # oid_index = item.oid.split('.')[-1]
        oid_index = item.oid_index
        hardware_obj = hardware_items.get(oid_index)
        if not hardware_obj:
            continue
        hardware_obj.value = item.value

    # entSensorStatus
    items = session.bulkwalk(oids[3])
    for item in items:
        # oid_index = item.oid.split('.')[-1]
        oid_index = item.oid_index
        hardware_obj = hardware_items.get(oid_index)
        if not hardware_obj:
            continue
        hardware_obj.state = item.value

    device.hardware = [h for h in hardware_items.values() if h.state is not None]

    return True


def fetch_interfaces(session, device):
    # Interface ...
    # num_if = session.get('ifNumber.0').value
    # num_if = int(num_if)

    oids = [
        '1.3.6.1.2.1.2.2.1.2',  # ifDescr
        # 'ifType',
        '1.3.6.1.2.1.2.2.1.10',  # ifInOctets
        '1.3.6.1.2.1.2.2.1.16',  # ifOutOctets
        '1.3.6.1.2.1.2.2.1.7',  # ifAdminStatus
        '1.3.6.1.2.1.2.2.1.8',  # ifOperStatus
        '1.3.6.1.2.1.2.2.1.5',  # ifSpeed
        '1.3.6.1.2.1.31.1.1.1.15',  # ifHighSpeed
        '1.3.6.1.2.1.31.1.1.1.18',  # ifAlias
    ]
    interfaces: List[SNMPVariable] = session.bulkwalk(oids)

    fetch_time = timezone.now()
    # pprint.pprint(interfaces)
    # device.interfaces = []

    interface_dict = {}
    for interface in device.interfaces:
        interface.previous_fetch_time = interface.fetch_time
        interface.fetch_time = fetch_time
        interface.previous_in_usage = interface.in_usage
        interface.previous_out_usage = interface.out_usage

        interface_dict[interface.oid_index] = interface

    for interface in interfaces:
        oid_index = int(interface.oid_index)
        device_if = interface_dict.setdefault(
            oid_index,
            DeviceInterface(oid_index=oid_index, fetch_time=fetch_time)
        )
        if interface.oid.startswith('.1.3.6.1.2.1.2.2.1.2'):
            device_if.description = interface.value
        elif interface.oid.startswith('.1.3.6.1.2.1.2.2.1.10'):
            device_if.in_usage = float(interface.value)
        elif interface.oid.startswith('.1.3.6.1.2.1.2.2.1.16'):
            device_if.out_usage = float(interface.value)
        elif "1.3.6.1.2.1.2.2.1.7" in interface.oid:
            admin_status = int(interface.value)
            device_if.admin_status = admin_status
        elif interface.oid.startswith('.1.3.6.1.2.1.2.2.1.8'):
            status = int(interface.value)
            # Initial history logs
            if device_if.status is None:
                h = DeviceInterfaceStatusHistory.objects.filter(
                    device=device,
                    description=device_if.description,
                    end_at__isnull=True
                ).first()
                if not h:
                    h = DeviceInterfaceStatusHistory(
                        device=device,
                        description=device_if.description,
                        status=status,
                        start_at=now,
                        created_at=now,
                    )
                    h.save()
            # Check if status not same
            elif device_if.status is not None and device_if.status != status:
                h = DeviceInterfaceStatusHistory.objects.filter(
                    device=device,
                    description=device_if.description,
                    end_at__isnull=True
                ).first()
                if h:
                    h.end_at = now
                    # Update end status
                    h.save()

                # Create new history with new status
                h = DeviceInterfaceStatusHistory(
                    device=device,
                    description=device_if.description,
                    status=status,
                    start_at=now,
                    created_at=now,
                )
                h.save()

                device_log = DeviceInterfaceStatusLog()
                device_log.device = device
                device_log.description = device_if.description
                device_log.oid_index = device_if.oid_index
                device_log.from_status = device_if.status
                device_log.to_status = status
                device_log.created_at = now
                device_log.save()

                # data = {
                #     'interface': device_if.description,
                #     'hostname': device.hostname,
                #     'ip_address': device.ip_address,
                #     'from_status': DeviceInterface.STATUS_TEXT[device_if.status],
                #     'to_status': DeviceInterface.STATUS_TEXT[status],
                #     'time': now
                # }

                notify_data = InterfaceNotifyData(
                    device_if.description,
                    device_if.alias,
                    device.hostname,
                    DeviceInterface.STATUS_TEXT[device_if.status],
                    DeviceInterface.STATUS_TEXT[status],
                    now,
                )

                # If node not down, notify
                if device.snmp_status:
                    notify_line_interface_status(notify_data)
                    send_email_interface_status(notify_data)

            device_if.status = status  # Backward compatible
            device_if.oper_status = status
        # elif interface.oid.startswith('.1.3.6.1.2.1.2.2.1.5'):
        elif "1.3.6.1.2.1.31.1.1.1.15" in interface.oid:
            device_if.speed = int(interface.value) * (10 ** 6)
        elif "1.3.6.1.2.1.31.1.1.1.18" in interface.oid:
            device_if.alias = interface.value

    device.interfaces = list(interface_dict.values())


def fetch_neighbor_cdp(session, device, update_type):
    cdp_oids = [
        '1.3.6.1.4.1.9.9.23.1.2.1.1.4',  # IPAddr
        '1.3.6.1.4.1.9.9.23.1.2.1.1.5',  # Version
        '1.3.6.1.4.1.9.9.23.1.2.1.1.6',  # Name
        '1.3.6.1.4.1.9.9.23.1.2.1.1.7'  # Port
    ]

    cdp_list = session.bulkwalk(cdp_oids)
    if not cdp_list:
        return False

    # Current neighbor
    if update_type == 'all':
        neighbors = []
    else:
        neighbors = device.neighbor

    neighbor_dict = {}
    neighbor_dict_temp = {}
    for neighbor in neighbors:
        neighbor_dict[neighbor.remote_ip_address] = neighbor

    for cdp in cdp_list:
        oid_index = cdp.oid.split('.')
        # oid_index = ".".join(oid_index[:-2:-1][::-1])
        oid_index = oid_index[-1]

        local_if_index = int(oid_index)
        neighbor = neighbor_dict_temp.setdefault(oid_index, Neighbor())
        neighbor.local_if_index = local_if_index

        if '23.1.2.1.1.4' in cdp.oid:
            neighbor.remote_ip_address = ".".join([str(ord(x)) for x in cdp.value])
        elif '23.1.2.1.1.5' in cdp.oid:
            neighbor.remote_version = cdp.value
        elif '23.1.2.1.1.6' in cdp.oid:
            neighbor.remote_hostname = cdp.value
        elif '23.1.2.1.1.7' in cdp.oid:
            neighbor.remote_port_description = cdp.value

    # Merge current neighbor and new neighbor
    for new_neighbor in neighbor_dict_temp.values():
        new_neighbor.source = 'cdp'
        neighbor_dict[new_neighbor.remote_ip_address] = new_neighbor

    device.neighbor = list(neighbor_dict.values())

    return True


def fetch_neighbor_lldp(session, device, update_type):
    """
    Fetch neighbor via LLDP
    More info: http://www.mibdepot.com/cgi-bin/getmib3.cgi?win=mib_a&r=cisco&f=LLDP-MIB-V1SMI.my&v=v1&t=tree

    :param session:
    :param device:
    :return:
    """

    remote_data_oid = [
        '1.0.8802.1.1.2.1.4.1.1.5',  # lldpRemChassisId
        '1.0.8802.1.1.2.1.4.1.1.8',  # lldpRemPortDesc
        '1.0.8802.1.1.2.1.4.1.1.9',  # lldpRemSysName
        '1.0.8802.1.1.2.1.4.1.1.10',  # lldpRemSysDesc
        '1.0.8802.1.1.2.1.4.2.1.4',  # lldpRemManAddrIfId
    ]

    remote_data = session.bulkwalk(remote_data_oid)
    if not remote_data:
        return False

    # Current neighbor
    if update_type == 'all':
        neighbors = []
    else:
        neighbors = device.neighbor

    neighbor_dict = {}
    neighbor_dict_temp = {}
    for neighbor in neighbors:
        neighbor_dict[neighbor.remote_chassis_id] = neighbor

    for lldp_remote_data in remote_data:
        oid_index = lldp_remote_data.oid.split('.')
        # oid_index = ".".join(oid_index[:-2:-1][::-1])
        oid_index = oid_index[-1]
        local_if_index = int(oid_index)
        neighbor = neighbor_dict_temp.setdefault(oid_index, Neighbor(local_if_index=local_if_index))
        if '4.1.1.5' in lldp_remote_data.oid:
            neighbor.remote_chassis_id = "".join(["{:02x}".format(ord(x)) for x in lldp_remote_data.value])
        elif '4.1.1.8' in lldp_remote_data.oid:
            neighbor.remote_port_description = lldp_remote_data.value
        elif '4.1.1.9' in lldp_remote_data.oid:
            neighbor.remote_hostname = lldp_remote_data.value
        elif '4.1.1.10' in lldp_remote_data.oid:
            neighbor.remote_version = lldp_remote_data.value
        # elif '4.2.1.4' in lldp_remote_data.oid:
        #     neighbor.

    # Merge current neighbor and new neighbor
    for new_neighbor in neighbor_dict_temp.values():
        new_neighbor.source = 'lldp'
        neighbor_dict[new_neighbor.remote_chassis_id] = new_neighbor

    device.neighbor = list(neighbor_dict.values())

    return False


def fetch_neighbor(session, device, update_type):
    cdp_work = fetch_neighbor_cdp(session, device, update_type)
    if cdp_work:
        return True
    lldp_work = fetch_neighbor_lldp(session, device, update_type)
    if lldp_work:
        return True

    # Reset
    # if update_type == 'all':
    #     device.neighbor = []
    return False


def fetch_cpu_usage(session, device):
    # https://www.mongodb.com/blog/post/schema-design-for-time-series-data-in-mongodb
    # https://www.cisco.com/c/en/us/support/docs/ip/simple-network-management-protocol-snmp/15215-collect-cpu-util-snmp.html
    oid = '.1.3.6.1.4.1.9.9.109.1.1.1.1.7.1'  # cpmCPUTotal1minRev

    cpu_usage = session.get(oid)
    now = timezone.now()
    timestamp_hour = now.replace(minute=0, second=0, microsecond=0)
    cpu_history = CpuHistory.objects.filter(device=device, timestamp_hour=timestamp_hour).first()
    if not cpu_history:
        cpu_history = CpuHistory(
            device=device,
            values={},
            num_samples=0,
            total_samples=0,
            timestamp_hour=timestamp_hour
        )
    values = cpu_history.values
    if values.get(str(now.minute)) is not None or cpu_usage.value == 'NOSUCHINSTANCE':
        print("None")
        return

    values[str(now.minute)] = float(cpu_usage.value)
    cpu_history.num_samples += 1
    cpu_history.total_samples += float(cpu_usage.value)

    cpu_history.save()


@shared_task
def fetch_snmp(hostname, update_type='snmp'):
    global now
    now = timezone.now()
    device = Device.objects.filter(ip_address=hostname).first()
    version = device.snmp_version
    if version == 'v3':
        username = device.snmp_username
        password = device.snmp_password
        session = Session(hostname, security_username=username, auth_password=password, version=3, use_numeric=True)
    elif version == 'v2' or version == 'v2c':
        community = device.snmp_community
        session = Session(hostname=hostname, community=community, version=2, use_numeric=True)
    else:
        session = Session(hostname=hostname, version=1, use_numeric=True)

    # Ping checking
    device.ping_status = True
    ping_test_times = Settings.objects.filter(key='ping_test_times').first()
    if not ping_test_times.value:
        ping_test_times = 1
    else:
        ping_test_times = int(ping_test_times.value)

    ping_result = ping(hostname, ping_test_times)
    if not ping_result:
        print("Ping timeout")
        device.ping_status = False
        # Todo notify host down

    try:
        fetch_basic_info(session, device)
        fetch_hardware_info(session, device)
        fetch_interfaces(session, device)

        fetch_hardware_info_2(session, device)

        fetch_neighbor(session, device, update_type)

        fetch_cpu_usage(session, device)

    except EasySNMPTimeoutError:
        device.status = False
        device.snmp_status = False
        if update_type == 'all':
            device.neighbor = []
        print("SNMP Timeout")

        # Todo
        # Change history from UP to DOWN
        dsh = DeviceStatusHistory.objects.filter(device=device, status=DeviceInterface.UP).filter(end_at__isnull=True)
        if dsh.count() != 0:
            dsh = dsh.first()
            dsh.end_at = now
            dsh.save()

            dsh = DeviceStatusHistory(
                device=device,
                ip_address=device.ip_address,
                hostname=device.hostname,
                sitename=device.sitename,
                object_id=device.object_id,
                status=DeviceInterface.DOWN,
                start_at=now,
                created_at=now,
            )

            dsh.save()

            # TODO: Notify node down
            notify_node_up_down(dsh)

            # Change status interface to down
            for device_interface in device.interfaces:
                if device_interface.status != DeviceInterface.DOWN:
                    # Save log history
                    h = DeviceInterfaceStatusHistory()
                    h.device = device
                    h.description = device_interface.description
                    h.status = DeviceInterface.DOWN
                    h.start_at = now
                    h.created_at = now
                    h.save()

                    device_interface.status = DeviceInterface.DOWN
    else:
        device.status = True
        device.snmp_status = True
        # Checking if Device status history has down change to up
        dsh = DeviceStatusHistory.objects.filter(device=device).filter(end_at__isnull=True).first()
        if dsh and dsh.status == DeviceInterface.DOWN:
            dsh.end_at = now
            dsh.save()
            # Notify node is up
            dsh.status = DeviceInterface.UP
            notify_node_up_down(dsh)

            dsh = DeviceStatusHistory(
                device=device,
                ip_address=device.ip_address,
                hostname=device.hostname,
                sitename=device.sitename,
                object_id=device.object_id,
                status=DeviceInterface.UP,
                start_at=now,
                created_at=now,
            )

            dsh.save()
        elif not dsh:
            dsh = DeviceStatusHistory(
                device=device,
                ip_address=device.ip_address,
                hostname=device.hostname,
                sitename=device.sitename,
                object_id=device.object_id,
                status=DeviceInterface.UP,
                start_at=now,
                created_at=now,
            )

            dsh.save()

    device.save()


@shared_task
def fetch_snmp_all():
    devices = Device.objects.all()
    g = []
    for device in devices:
        g.append(fetch_snmp.s(device.ip_address))

    job = group(g)
    job.apply_async()


def notify_node_up_down(dsh: DeviceStatusHistory) -> None:
    settings = {x.key: x.value for x in Settings.objects.all()}

    data = {
        'hostname': dsh.device.hostname,
        'ip_address': dsh.device.ip_address,
        'start_at': dsh.start_at,
        'end_at': dsh.end_at,
        'status': DeviceInterface.STATUS_TEXT[dsh.status],
    }

    if dsh.end_at is not None:
        # Node changed status from down to up
        line_message = settings.get(
            'line_node_up_notify_message',
            SETTING_DEFAULT.get('line_node_up_notify_message')).format(**data)
        message = settings.get(
            'email_node_up_notify_message',
            SETTING_DEFAULT.get('email_node_up_notify_message')).format(**data)
        header = settings.get(
            'email_node_up_notify_header',
            SETTING_DEFAULT.get('email_node_up_notify_header')).format(**data)

    else:
        line_message = settings.get(
            'line_node_down_notify_message',
            SETTING_DEFAULT.get('line_node_down_notify_message')).format(**data)
        message = settings.get(
            'email_node_down_notify_message',
            SETTING_DEFAULT.get('email_node_down_notify_message')).format(**data)
        header = settings.get('email_node_down_notify_header',
                              SETTING_DEFAULT.get('email_node_down_notify_header')).format(**data)

    send_email.delay(settings, header, message)
    line_notify.delay(line_message)


def send_email_interface_status(data: InterfaceNotifyData) -> None:
    settings = {x.key: x.value for x in Settings.objects.all()}

    message = settings.get('email_notify_message', SETTING_DEFAULT.get('email_notify_message')).format(**data._asdict())
    header = settings.get('email_notify_header', SETTING_DEFAULT.get('email_notify_header')).format(**data._asdict())

    send_email.delay(settings, header, message)


@shared_task
def send_email(settings: dict, header: str, message: str) -> None:
    """
    Send email task
    :param data: NotifyData
    :param settings:
    :param header:
    :param message:
    :return:
    """
    # settings = {x.key: x.value for x in Settings.objects.all()}

    if settings.get('smtp_port'):
        port = int(settings.get('smtp_port'))
    else:
        port = 25

    if settings.get('smtp_use_tls') == 'on':
        use_tls = True
    else:
        use_tls = False

    if settings.get('smtp_use_ssl') == 'on':
        use_ssl = True
    else:
        use_ssl = False

    email_obj = EmailBackend(
        host=settings.get('smtp_host'),
        port=port,
        username=settings.get('smtp_username'),
        password=settings.get('smtp_password'),
        use_tls=use_tls,
        use_ssl=use_ssl
    )

    email_list = [email.strip() for email in settings.get('email_notify_to').split(',')]
    sender_email = settings.get('smtp_email')
    if len(email_list) == 0 or not sender_email:
        return

    email = EmailMessage(
        header,
        message,
        sender_email,
        email_list,
    )
    email_obj.send_messages([email])
