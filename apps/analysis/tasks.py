"""
Background tasks for analysis using Django-Q2.
"""
from django_q.tasks import async_task
from apps.papers.models import Paper
from apps.subjects.models import Subject


def analyze_paper_task(paper_id: str):
    """
    Background task to analyze a paper.
    Called via Django-Q2.
    """
    from .pipeline import AnalysisPipeline
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        paper = Paper.objects.get(id=paper_id)
        paper.status = Paper.ProcessingStatus.PROCESSING
        paper.save()
        
        logger.info(f"Starting analysis for paper {paper.id}: {paper.title}")
        
        # Run analysis without LLM for speed (use keyword-based classification)
        # LLM is too slow for real-time processing
        pipeline = AnalysisPipeline(llm_client=None)
        job = pipeline.analyze_paper(paper)
        
        logger.info(f"Analysis completed for paper {paper.id}. Status: {job.status}")
        
    except Paper.DoesNotExist:
        logger.error(f"Paper {paper_id} not found")
    except Exception as e:
        logger.exception(f"Analysis failed for paper {paper_id}: {e}")
        try:
            paper = Paper.objects.get(id=paper_id)
            paper.status = Paper.ProcessingStatus.FAILED
            paper.processing_error = str(e)
            paper.save()
        except Exception:
            pass


def analyze_subject_topics_task(subject_id: str):
    """
    Background task to analyze topics for a subject.
    Performs clustering and repetition analysis.
    """
    from apps.analytics.clustering import analyze_subject_topics
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        subject = Subject.objects.get(id=subject_id)
        logger.info(f"Starting topic analysis for subject {subject.id}: {subject.name}")
        
        # Run topic clustering analysis
        results = analyze_subject_topics(subject)
        
        logger.info(f"Topic analysis completed for subject {subject.id}. "
                   f"Created {results.get('clusters_created', 0)} clusters, "
                   f"processed {results.get('questions_processed', 0)} questions")
        
        return results
        
    except Subject.DoesNotExist:
        logger.error(f"Subject {subject_id} not found")
    except Exception as e:
        logger.exception(f"Topic analysis failed for subject {subject_id}: {e}")
        raise  # Re-raise to mark task as failed in Django-Q


def queue_paper_analysis(paper: Paper):
    """Queue a paper for background analysis."""
    async_task(
        'apps.analysis.tasks.analyze_paper_task',
        str(paper.id),
        task_name=f'analyze_paper_{paper.id}'
    )


def queue_topic_analysis(subject: Subject):
    """Queue topic clustering analysis for a subject."""
    async_task(
        'apps.analysis.tasks.analyze_subject_topics_task',
        str(subject.id),
        task_name=f'analyze_topics_{subject.id}'
    )
