import re

from djongo import models

from .snmp_utils import oid_product_cisco


class Neighbor(models.Model):
    class Meta:
        abstract = True

    source = models.CharField()  # CDP or LLDP or Other.
    local_if_index = models.IntegerField(null=True)

    remote_ip_address = models.CharField()
    remote_version = models.CharField()  # Aka sysDescription
    remote_hostname = models.CharField()
    remote_port_description = models.CharField()
    remote_chassis_id = models.CharField(null=True)


class Hardware(models.Model):
    class Meta:
        abstract = True

    description = models.CharField()
    state = models.IntegerField()
    value = models.IntegerField()
    threshold = models.IntegerField()

    def __str__(self):
        return "{} is {}".format(self.description, self.value)


class Temperature(models.Model):
    class Meta:
        abstract = True

    description = models.CharField()
    state = models.IntegerField()
    value = models.IntegerField()
    threshold = models.IntegerField()

    def __str__(self):
        return "{} is {}".format(self.description, self.value)


class Fans(models.Model):
    class Meta:
        abstract = True

    description = models.CharField()
    state = models.IntegerField()


class PowerSupply(models.Model):
    class Meta:
        abstract = True

    description = models.CharField()
    state = models.IntegerField()


class DeviceInterface(models.Model):
    class Meta:
        abstract = True

    UP = 1
    DOWN = 2
    TESTING = 3

    STATUS_TEXT = {
        UP: 'UP',
        DOWN: 'DOWN',
        TESTING: 'TESTING'
    }

    previous_fetch_time = models.DateTimeField()
    fetch_time = models.DateTimeField()

    previous_in_usage = models.FloatField(default=0.0)
    previous_out_usage = models.FloatField(default=0.0)
    in_usage = models.FloatField(default=0.0)
    out_usage = models.FloatField(default=0.0)

    status = models.IntegerField(null=True)
    admin_status = models.IntegerField(null=True)
    oper_status = models.IntegerField(null=True)

    description = models.CharField(max_length=255)

    alias = models.CharField(max_length=255)

    speed = models.IntegerField(default=0)

    # use for SNMP
    oid_index = models.IntegerField()

    def in_usage_bps(self):
        if self.speed <= 0:
            return 0
        in_time = self.fetch_time - self.previous_fetch_time
        in_time = in_time.seconds + (in_time.microseconds / 1000000)
        return ((self.in_usage - self.previous_in_usage) * 8) / in_time

    def out_usage_bps(self):
        if self.speed <= 0:
            return 0
        in_time = self.fetch_time - self.previous_fetch_time
        in_time = in_time.seconds + (in_time.microseconds / 1000000)
        return ((self.out_usage - self.previous_out_usage) * 8) / in_time

    def in_usage_percent(self):
        if self.speed <= 0:
            return '{:.2f}'.format(0.0)
        in_time = self.fetch_time - self.previous_fetch_time
        in_time = in_time.seconds + (in_time.microseconds / 1000000)
        percent = (((self.in_usage - self.previous_in_usage) * 8) / (
                in_time * self.speed)) * 100
        print(self.description, self.in_usage, self.previous_in_usage, in_time,
              self.speed)
        return "{percent:.{point:}f}".format(percent=percent, point=2)

    def out_usage_percent(self):
        if self.speed <= 0:
            return '{:.2f}'.format(0.0)
        in_time = self.fetch_time - self.previous_fetch_time
        in_time = in_time.seconds + (in_time.microseconds / 1000000)
        percent = (((self.out_usage - self.previous_out_usage) * 8) / (
                in_time * self.speed)) * 100
        return "{percent:.{point:}f}".format(percent=percent, point=2)

    def __str__(self):
        return str(self.oid_index)


class Device(models.Model):
    ip_address = models.CharField(max_length=255, unique=True)
    netmask = models.CharField(max_length=255, null=True)  # Netmask ipAdEntNetMask
    hostname = models.CharField(max_length=255, blank=True)
    sitename = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    object_id = models.CharField(max_length=255, blank=True)
    uptime = models.IntegerField(default=-1)

    status = models.BooleanField(default=False)

    snmp_version = models.CharField(max_length=10, blank=True)
    snmp_community = models.CharField(max_length=255, blank=True)
    snmp_username = models.CharField(max_length=255, blank=True)
    snmp_password = models.CharField(max_length=255, blank=True)
    # Polling interval
    snmp_polling_local_interval = models.BooleanField(default=False)
    snmp_polling_interval = models.IntegerField(default=0)

    # Status
    ping_status = models.BooleanField(default=False)
    snmp_status = models.BooleanField(default=False)

    # Interfaces
    interfaces = models.ArrayModelField(
        model_container=DeviceInterface,
        default=[]
    )

    # Neighbor
    neighbor = models.ArrayModelField(
        model_container=Neighbor,
        default=[]
    )

    # Fans
    fans = models.ArrayModelField(
        model_container=Fans,
        default=[]
    )

    # PowerSupply
    power_supplies = models.ArrayModelField(
        model_container=PowerSupply,
        default=[]
    )

    # Temperature
    temperature = models.ArrayModelField(
        model_container=Temperature,
        default=[]
    )

    # Hardware
    hardware = models.ArrayModelField(
        model_container=Hardware,
        default=[],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hardware_status = None

    def get_manufacturer(self):
        if 'cisco' in self.description:
            return 'cisco'

    def get_version(self):
        pass

    def is_down(self):
        return not self.ping_status or not self.snmp_status or not self.status_ok()

    def status_ok(self):
        if self.hardware_status is not None:
            return self.hardware_status

        if not self.ping_status or not self.snmp_status:
            self.hardware_status = False
            return False

        for fan in self.fans:
            if not fan.state:
                self.hardware_status = False
                return False

        for psu in self.power_supplies:
            if not psu.state:
                self.hardware_status = False
                return False

        for t in self.temperature:
            if not t.state:
                self.hardware_status = False
                return False

        for h in self.hardware:
            if not h.state:
                self.hardware_status = False
                return False

        self.hardware_status = True
        return True

    @property
    def is_router(self):
        if not self.object_id:
            return False
        object_name = oid_product_cisco.get(self.object_id.strip('.'))
        if not object_name:
            return False

        test = re.compile(r'cisco(ASR)?([0-9]+)')
        if test.match(object_name):
            return True

        return False

    @property
    def is_switch(self):
        if not self.object_id:
            return False
        object_name = oid_product_cisco.get(self.object_id.strip('.'))
        if not object_name:
            return False

        if object_name.startswith('catalyst') or object_name.startswith('catWs'):
            return True

        test = re.compile(r'(cat)?(ciscoMe)?([0-9]+)')
        if test.match(object_name):
            return True

        return False


class DeviceInterfaceStatusLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)

    description = models.CharField(max_length=255)

    from_status = models.IntegerField(default=0)
    to_status = models.IntegerField(default=0)
    oid_index = models.IntegerField()

    created_at = models.DateTimeField()


class DeviceInterfaceStatusHistory(models.Model):
    """
    This collecting device status history for status is not UP
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE)

    description = models.CharField(max_length=255)

    # ip_address = models.CharField(max_length=255)
    # hostname = models.CharField(max_length=255, blank=True)
    # sitename = models.CharField(max_length=255, blank=True)
    # object_id = models.CharField(max_length=255, blank=True)

    status = models.IntegerField()

    start_at = models.DateTimeField(null=True)
    end_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField()


class DeviceStatusHistory(models.Model):
    """
    This collecting device status history for status is not UP
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE)

    ip_address = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255, blank=True)
    sitename = models.CharField(max_length=255, blank=True)
    object_id = models.CharField(max_length=255, blank=True)

    status = models.IntegerField()

    start_at = models.DateTimeField(null=True)
    end_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField()


class CpuHistory(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)

    values = models.DictField(default={})

    num_samples = models.IntegerField(default=0)
    total_samples = models.FloatField(default=0.0)

    timestamp_hour = models.DateTimeField()


class DeviceObjectId(models.Model):
    object_id = models.CharField(max_length=255, primary_key=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=255)
    device_type_name = models.CharField(max_length=255, blank=True)
