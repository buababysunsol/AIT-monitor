from django import forms

SNMP_VERSION_CHOICE = (
    ('v1', 'version 1'),
    ('v2c', 'version 2c'),
    ('v3', 'version3')
)


class AddManualForm(forms.Form):
    old_ip_address = forms.CharField(max_length=255, required=False)

    sitename = forms.CharField(max_length=255, required=False)

    ip_address = forms.CharField(max_length=255)
    snmp_version = forms.ChoiceField(choices=SNMP_VERSION_CHOICE)

    snmp_community = forms.CharField(required=False)
    snmp_username = forms.CharField(required=False)
    snmp_password = forms.CharField(required=False)

    def clean(self):
        super().clean()
        ip_address = self.cleaned_data.get('ip_address')
        if not ip_address:
            self.add_error('ip_address', 'IP Address is required.')

        snmp_ver = self.cleaned_data.get('snmp_version')
        if snmp_ver == 'v2c':
            self._check_ver2c()
        elif snmp_ver == 'v3':
            self._check_ver3()

    def _check_ver2c(self):
        snmp_community = self.cleaned_data.get('snmp_community')
        if not snmp_community:
            self.add_error('snmp_community', 'SNMP Community is required.')

    def _check_ver3(self):
        snmp_username = self.cleaned_data.get('snmp_username')
        snmp_password = self.cleaned_data.get('snmp_password')
        if not snmp_username:
            self.add_error('snmp_username', 'SNMP Username is required.')

        if not snmp_password:
            self.add_error('snmp_password', 'SNMP Password is required.')


class AddDiscoverForm(forms.Form):
    snmp_version = forms.ChoiceField(choices=SNMP_VERSION_CHOICE)

    snmp_community = forms.CharField(required=False)
    snmp_username = forms.CharField(required=False)
    snmp_password = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        post = args[0]

        for name, data in post.items():
            if name.startswith('ip_'):
                self.fields[name] = forms.CharField()
            elif name.startswith('status_'):
                self.fields[name] = forms.CharField()

    def clean(self):
        super().clean()

        snmp_ver = self.cleaned_data.get('snmp_version')
        if snmp_ver == 'v2c':
            self._check_ver2c()
        elif snmp_ver == 'v3':
            self._check_ver3()

    def _check_ver2c(self):
        snmp_community = self.cleaned_data.get('snmp_community')
        if not snmp_community:
            self.add_error('snmp_community', 'SNMP Community is required.')

    def _check_ver3(self):
        snmp_username = self.cleaned_data.get('snmp_username')
        snmp_password = self.cleaned_data.get('snmp_password')
        if not snmp_username:
            self.add_error('snmp_username', 'SNMP Username is required.')

        if not snmp_password:
            self.add_error('snmp_password', 'SNMP Password is required.')
