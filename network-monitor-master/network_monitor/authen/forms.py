from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class AuthForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100)


class UserCreationNewForm(UserCreationForm):
    # first_name = forms.CharField(max_length=64, required=True)
    # last_name = forms.CharField(max_length=64, required=True)
    # email = forms.EmailField(max_length=254, required=True)

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'email', 'first_name', 'last_name',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        counter = User.objects.filter(email=email).count()
        if email and counter > 0:
            raise forms.ValidationError(u'This email address is already registered.')
        return email
