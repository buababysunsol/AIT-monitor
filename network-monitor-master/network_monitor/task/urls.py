from django.urls import path
from .views import list_task

urlpatterns = [
    path('', list_task, name='list-task'),
]
