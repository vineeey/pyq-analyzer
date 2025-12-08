"""URL patterns for analytics app."""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('subject/<uuid:subject_pk>/', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    path('subject/<uuid:subject_pk>/api/', views.AnalyticsAPIView.as_view(), name='api'),
    path('subject/<uuid:subject_pk>/api/topic-priority/', views.TopicPriorityAPIView.as_view(), name='topic_priority_api'),
]
