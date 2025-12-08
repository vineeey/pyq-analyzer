"""
Action views for subject operations (analyze, cluster, etc.)
"""
import logging
from django.db import models
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse

from apps.subjects.models import Subject
from apps.papers.models import Paper
from apps.analysis.pipeline import AnalysisPipeline

logger = logging.getLogger(__name__)


class AnalyzeSubjectView(LoginRequiredMixin, View):
    """
    Trigger analysis for all unprocessed papers in a subject.
    """
    
    def post(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        # Get unprocessed papers
        pending_papers = Paper.objects.filter(
            subject=subject,
            status=Paper.ProcessingStatus.PENDING
        )
        
        if not pending_papers.exists():
            messages.info(request, 'No pending papers to analyze.')
            return redirect('subjects:detail', pk=subject_pk)
        
        # Start analysis pipeline for each paper
        pipeline = AnalysisPipeline()
        success_count = 0
        error_count = 0
        
        for paper in pending_papers:
            try:
                paper.status = Paper.ProcessingStatus.PROCESSING
                paper.save()
                
                job = pipeline.analyze_paper(paper)
                
                if job.status == 'completed':
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Analysis failed for paper {paper.id}: {e}")
                error_count += 1
                paper.status = Paper.ProcessingStatus.FAILED
                paper.processing_error = str(e)
                paper.save()
        
        # Message based on results
        if success_count > 0:
            messages.success(
                request,
                f'Successfully analyzed {success_count} paper(s)!'
            )
        
        if error_count > 0:
            messages.warning(
                request,
                f'{error_count} paper(s) failed to analyze.'
            )
        
        # Trigger clustering in background if available
        try:
            from django_q.tasks import async_task
            from apps.analytics.tasks import cluster_subject_topics
            async_task(cluster_subject_topics, str(subject.id))
            messages.info(request, 'Topic clustering started in background...')
        except ImportError:
            # Run clustering synchronously if Django-Q not available
            try:
                from services.clustering.topic_clusterer import TopicClusterer
                clusterer = TopicClusterer()
                clusters = clusterer.cluster_subject_questions(subject)
                messages.success(
                    request,
                    f'Created {sum(len(c) for c in clusters.values())} topic clusters'
                )
            except Exception as e:
                logger.error(f"Clustering failed: {e}")
                messages.warning(request, 'Clustering failed. Check logs for details.')
        
        return redirect('subjects:detail', pk=subject_pk)


class TriggerClusteringView(LoginRequiredMixin, View):
    """
    Manually trigger topic clustering for a subject.
    """
    
    def post(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        # Check if there are questions to cluster
        question_count = subject.papers.aggregate(
            total=models.Count('questions')
        )['total'] or 0
        
        if question_count == 0:
            messages.warning(request, 'No questions found to cluster. Analyze papers first.')
            return redirect('subjects:detail', pk=subject_pk)
        
        try:
            # Try async first
            from django_q.tasks import async_task
            from apps.analytics.tasks import cluster_subject_topics
            async_task(cluster_subject_topics, str(subject.id))
            messages.success(request, 'Clustering task queued successfully!')
        except ImportError:
            # Fall back to synchronous
            try:
                from services.clustering.topic_clusterer import TopicClusterer
                from apps.analytics.calculator import StatsCalculator
                
                clusterer = TopicClusterer()
                clusters = clusterer.cluster_subject_questions(subject)
                
                total_clusters = sum(len(c) for c in clusters.values())
                
                # Cache analytics
                calculator = StatsCalculator(subject)
                calculator.cache_analytics()
                
                messages.success(
                    request,
                    f'Successfully created {total_clusters} topic clusters!'
                )
            except Exception as e:
                logger.error(f"Clustering failed: {e}", exc_info=True)
                messages.error(request, f'Clustering failed: {str(e)}')
        
        return redirect('analytics:dashboard', subject_pk=subject_pk)


class ConfigureExamPatternView(LoginRequiredMixin, View):
    """
    Configure exam pattern for a subject.
    """
    
    def post(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        pattern_name = request.POST.get('pattern_name', 'ktu_standard')
        
        try:
            subject.set_exam_pattern(pattern_name=pattern_name)
            messages.success(
                request,
                f'Exam pattern set to {pattern_name.replace("_", " ").title()}'
            )
        except Exception as e:
            logger.error(f"Failed to set exam pattern: {e}")
            messages.error(request, 'Failed to set exam pattern.')
        
        return redirect('subjects:detail', pk=subject_pk)
