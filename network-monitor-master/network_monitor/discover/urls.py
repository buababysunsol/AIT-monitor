from django.urls import path
from discover import views

urlpatterns = [
    path('', views.Discover.as_view(), name="discover-device"),
    path('add/manual/', views.AddManual.as_view(), name="device-add-manual"),
    path('add/discover/', views.AddDiscover.as_view(), name="device-add-discover")
]
