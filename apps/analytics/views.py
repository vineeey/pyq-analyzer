"""Views for analytics dashboard."""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from apps.subjects.models import Subject
from .calculator import StatsCalculator


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Analytics dashboard for a subject."""
    
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = get_object_or_404(
            Subject, pk=self.kwargs['subject_pk'], user=self.request.user
        )
        
        calculator = StatsCalculator(subject)
        stats = calculator.get_complete_stats()
        
        # Prepare chart data
        module_dist = stats['module_distribution']
        module_labels = [m['module'] for m in module_dist]
        module_data = [m['count'] for m in module_dist]
        
        bloom_dist = stats.get('bloom_distribution', {})
        bloom_data = [
            bloom_dist.get('remember', 0),
            bloom_dist.get('understand', 0),
            bloom_dist.get('apply', 0),
            bloom_dist.get('analyze', 0),
            bloom_dist.get('evaluate', 0),
            bloom_dist.get('create', 0),
        ]
        
        difficulty_dist = stats.get('difficulty_distribution', {})
        difficulty_data = [
            difficulty_dist.get('easy', 0),
            difficulty_dist.get('medium', 0),
            difficulty_dist.get('hard', 0),
        ]
        
        year_trend = stats.get('year_trend', [])
        year_labels = [y['year'] for y in year_trend]
        year_data = [y['question_count'] for y in year_trend]
        
        # Topic clusters for priority display
        topic_clusters = stats.get('topic_clusters', [])
        top_priority_topics = [t for t in topic_clusters if t.get('priority_tier') == 1][:10]
        
        context.update({
            'subject': subject,
            'stats': stats,
            'module_labels': module_labels,
            'module_data': module_data,
            'bloom_data': bloom_data,
            'difficulty_data': difficulty_data,
            'year_labels': year_labels,
            'year_data': year_data,
            'top_priority_topics': top_priority_topics,
            'module_stats': module_dist,
            'repeated_questions': top_priority_topics,  # For compatibility with template
        })
        
        return context


class AnalyticsAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for analytics data (for Chart.js)."""
    
    def get(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        calculator = StatsCalculator(subject)
        return JsonResponse(calculator.get_complete_stats(), safe=False)


class TopicPriorityAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for topic priority chart data."""
    
    def get(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        calculator = StatsCalculator(subject)
        top_topics_by_module = calculator.get_top_topics_by_module(top_n=3)
        
        # Flatten and prepare for chart
        chart_data = {
            'labels': [],
            'datasets': []
        }
        
        # Organize by module
        for module_num in sorted(top_topics_by_module.keys()):
            topics = top_topics_by_module[module_num]
            for topic in topics:
                chart_data['labels'].append(f"M{module_num}: {topic['topic_name'][:30]}")
        
        # Create dataset with frequencies
        frequencies = []
        colors = []
        
        for module_num in sorted(top_topics_by_module.keys()):
            topics = top_topics_by_module[module_num]
            for topic in topics:
                frequencies.append(topic['frequency'])
                # Color based on priority
                tier = topic.get('priority_tier', 4)
                if tier == 1:
                    colors.append('rgba(239, 68, 68, 0.8)')  # Red
                elif tier == 2:
                    colors.append('rgba(249, 115, 22, 0.8)')  # Orange
                elif tier == 3:
                    colors.append('rgba(34, 197, 94, 0.8)')  # Green
                else:
                    colors.append('rgba(59, 130, 246, 0.8)')  # Blue
        
        chart_data['datasets'] = [{
            'label': 'Frequency',
            'data': frequencies,
            'backgroundColor': colors,
            'borderWidth': 1
        }]
        
        return JsonResponse(chart_data)
