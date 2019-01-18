from django.urls import path

from .views import login_view, logout_view, userlist_view, register_view, remove_view

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('user/', userlist_view, name='userlist'),
    path('register/', register_view, name='register'),
    path('remove/', remove_view, name='remove-user'),
]
