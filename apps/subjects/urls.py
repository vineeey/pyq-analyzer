"""
URL patterns for subjects app.
"""
from django.urls import path
from . import views
from . import actions

app_name = 'subjects'

urlpatterns = [
    # Subject URLs
    path('', views.SubjectListView.as_view(), name='list'),
    path('create/', views.SubjectCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.SubjectDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.SubjectUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.SubjectDeleteView.as_view(), name='delete'),
    
    # Module URLs
    path('<uuid:subject_pk>/modules/create/', views.ModuleCreateView.as_view(), name='module_create'),
    path('modules/<uuid:pk>/edit/', views.ModuleUpdateView.as_view(), name='module_update'),
    path('modules/<uuid:pk>/delete/', views.ModuleDeleteView.as_view(), name='module_delete'),
    
    # Action URLs
    path('<uuid:subject_pk>/analyze/', actions.AnalyzeSubjectView.as_view(), name='analyze'),
    path('<uuid:subject_pk>/cluster/', actions.TriggerClusteringView.as_view(), name='cluster'),
    path('<uuid:subject_pk>/configure-pattern/', actions.ConfigureExamPatternView.as_view(), name='configure_pattern'),
]
