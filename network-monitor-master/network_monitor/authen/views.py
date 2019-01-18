from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, logout, login

from authen.decorators import is_superuser
from device.models import Device
from .forms import AuthForm, UserCreationNewForm
import logging

logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == 'POST':
        form = AuthForm(request.POST)

        if not form.is_valid():
            messages.warning(request, 'Username or password not match.')
            return render(request, 'authen/login.html', {'form': form})

        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.warning(request, 'Username or password not match.')
        else:
            login(request, user)
            return redirect('search-device')
    else:
        form = AuthForm()

    return render(request, 'authen/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@is_superuser
def userlist_view(request):
    users = User.objects.all()

    return render(request, 'authen/userlist.html', {'users': users})


@is_superuser
def register_view(request):
    if request.method == 'POST':
        form = UserCreationNewForm(request.POST)
        if form.is_valid():
            group, created = Group.objects.get_or_create(name='normal_group')
            if created:
                ct_device = ContentType.objects.get_for_model(Device)
                # ct_report = ContentType.objects.get_for_model()
                permission = Permission.objects.get(
                    codename='view_device',
                    content_type=ct_device
                )
                group.permissions.add(permission)
            user = form.save()
            superuser = request.POST.get('is_superuser')

            if superuser == 'on':
                user.is_superuser = True
                user.save()

            user.groups.add(group)
            messages.success(request, 'Created user {} successfully.'.format(form.cleaned_data['username']))
            return redirect('userlist')
        else:
            logger.error(form.errors)
            for field, error in form.errors.as_data().items():
                messages.error(request, "{} \"{}\"".format(field, error[0].message))
    else:
        form = UserCreationNewForm()
    return render(request, 'authen/register.html', {'form': form})


@is_superuser
def remove_view(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        user = User.objects.filter(pk=user_id)
        if user.count() > 0:
            username = user.username
            user.delete()
            messages.success(request, "Remove user {} success.".format(username))

    return redirect('userlist')
