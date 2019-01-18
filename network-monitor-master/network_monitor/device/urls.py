from django.urls import path
from .views import DeviceListView, EditDeviceView, SearchDeviceView, device_view, device_network, delete_device

urlpatterns = [
    path('', DeviceListView.as_view(), name='list-device'),
    path('edit/', EditDeviceView.as_view(), name='edit-device'),
    path('search/', SearchDeviceView.as_view(), name='search-device'),
    path('network/', device_network, name='device-network'),
    path('<int:id>/', device_view, name='view-device'),
    path('<int:id>/delete', delete_device, name='delete-device')
]
