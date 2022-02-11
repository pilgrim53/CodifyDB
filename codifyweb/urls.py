from django.urls import include, path
from django.views.generic import TemplateView
from . import views
    # path('checklist/', views.checklist, name='checklist'),
    # path('target/', views.target_list, name='targetlist'),
    # path('', include('django.contrib.auth.urls')),
    # path('inventory', views.TargetListView.as_view(), name='inventory'),
    # path('', TemplateView.as_view(template_name="home.html"), name='home'),

urlpatterns = [
    path('', views.index, name='index'),
    path('test', views.test, name='test'),
    path('add_target', views.add_target, name='add_target'),
    path('check_target', views.check_target, name='check_target'),
    path('scan_target', views.scan_target, name='scan_target'),
    path('export_target', views.export_target, name='export_target'),
    path('add_update', views.add_update, name='add_update'),
    path('run_report', views.run_report, name='run_report')
]
    
