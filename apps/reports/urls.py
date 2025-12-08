"""URL patterns for reports app."""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('subject/<uuid:subject_pk>/', views.ReportsListView.as_view(), name='list'),
    path('subject/<uuid:subject_pk>/module/<int:module_number>/', views.GenerateModuleReportView.as_view(), name='module_report'),
    path('subject/<uuid:subject_pk>/all/', views.GenerateAllModuleReportsView.as_view(), name='all_modules'),
    path('subject/<uuid:subject_pk>/analytics/', views.GenerateAnalyticsReportView.as_view(), name='analytics_report'),
]
