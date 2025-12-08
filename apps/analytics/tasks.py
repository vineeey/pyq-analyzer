"""
Background tasks for analytics processing.
"""
import logging
from django.utils import timezone

from services.clustering.topic_clusterer import TopicClusterer
from apps.subjects.models import Subject
from apps.analytics.calculator import StatsCalculator

logger = logging.getLogger(__name__)


def cluster_subject_topics(subject_id: str):
    """
    Background task to cluster topics for a subject.
    Should be run after papers are analyzed.
    
    Args:
        subject_id: UUID of the subject
    """
    try:
        subject = Subject.objects.get(id=subject_id)
        logger.info(f"Starting topic clustering for subject: {subject.name}")
        
        # Create clusterer
        clusterer = TopicClusterer(similarity_threshold=0.75)
        
        # Perform clustering
        clusters = clusterer.cluster_subject_questions(subject)
        
        total_clusters = sum(len(c) for c in clusters.values())
        logger.info(f"Created {total_clusters} topic clusters across {len(clusters)} modules")
        
        # Cache analytics
        calculator = StatsCalculator(subject)
        analytics = calculator.cache_analytics()
        logger.info(f"Cached analytics for subject {subject.name}")
        
        return {
            'success': True,
            'subject_id': str(subject_id),
            'clusters_created': total_clusters,
            'modules_processed': len(clusters),
        }
        
    except Subject.DoesNotExist:
        logger.error(f"Subject {subject_id} not found")
        return {'success': False, 'error': 'Subject not found'}
    except Exception as e:
        logger.error(f"Clustering failed for subject {subject_id}: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def update_subject_analytics(subject_id: str):
    """
    Update cached analytics for a subject.
    
    Args:
        subject_id: UUID of the subject
    """
    try:
        subject = Subject.objects.get(id=subject_id)
        calculator = StatsCalculator(subject)
        analytics = calculator.cache_analytics()
        
        logger.info(f"Updated analytics for subject {subject.name}")
        return {'success': True, 'subject_id': str(subject_id)}
        
    except Subject.DoesNotExist:
        logger.error(f"Subject {subject_id} not found")
        return {'success': False, 'error': 'Subject not found'}
    except Exception as e:
        logger.error(f"Analytics update failed for subject {subject_id}: {e}")
        return {'success': False, 'error': str(e)}
