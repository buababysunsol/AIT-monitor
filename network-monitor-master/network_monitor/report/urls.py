from django.urls import path
from .views import report_link, report_link_new, report, export_csv, report_node_updown

urlpatterns = [
    path('', report, name='report-index'),
    path('link', report_link, name='report-link'),
    path('link/new', report_link_new, name='report-link-new'),
    path('link/export', export_csv, name='report-link-export'),
    path('link/<int:device_id>', report_link, name='report-link'),
    path('nodeupdown', report_node_updown, name='report-node-updown'),
]
