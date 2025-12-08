"""URL patterns for reports app."""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('subject/<uuid:subject_pk>/module/', views.GenerateModuleReportView.as_view(), name='module_report'),
    path('subject/<uuid:subject_pk>/analytics/', views.GenerateAnalyticsReportView.as_view(), name='analytics_report'),
    # Module-wise reports
    path('subject/<uuid:subject_pk>/modules/', views.ModuleReportsView.as_view(), name='module_reports'),
    path('subject/<uuid:subject_pk>/modules/generate-all/', views.GenerateAllModuleReportsView.as_view(), name='generate_all_modules'),
    path('subject/<uuid:subject_pk>/modules/<uuid:module_pk>/download/', views.GenerateSingleModuleReportView.as_view(), name='download_module_report'),
]
