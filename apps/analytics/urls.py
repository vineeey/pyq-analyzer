"""URL patterns for analytics app."""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('subject/<uuid:subject_pk>/', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    path('subject/<uuid:subject_pk>/module/<int:module_number>/', views.ModuleAnalyticsView.as_view(), name='module'),
    path('subject/<uuid:subject_pk>/api/', views.AnalyticsAPIView.as_view(), name='api'),
    path('subject/<uuid:subject_pk>/analyze/', views.TriggerTopicAnalysisView.as_view(), name='trigger_analysis'),
]
