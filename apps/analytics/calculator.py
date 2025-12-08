"""
Statistics calculator for analytics dashboard.
"""
from typing import Dict, Any, List
from collections import Counter
from django.db.models import Count, Avg, Q

from apps.questions.models import Question
from apps.subjects.models import Subject
from apps.analytics.models import TopicCluster, SubjectAnalytics


class StatsCalculator:
    """Calculates statistics for a subject."""
    
    def __init__(self, subject: Subject):
        self.subject = subject
        self.questions = Question.objects.filter(paper__subject=subject)
    
    def get_overview(self) -> Dict[str, Any]:
        """Get overview statistics."""
        total_questions = self.questions.count()
        unique_questions = self.questions.filter(is_duplicate=False).count()
        duplicates = total_questions - unique_questions
        
        return {
            'total_questions': total_questions,
            'unique_questions': unique_questions,
            'duplicates': duplicates,
            'duplicate_percentage': round(duplicates / total_questions * 100, 1) if total_questions else 0,
            'papers_count': self.subject.papers.count(),
            'modules_count': self.subject.modules.count(),
        }
    
    def get_module_distribution(self) -> List[Dict[str, Any]]:
        """Get question distribution across modules."""
        modules = self.subject.modules.all()
        distribution = []
        
        for module in modules:
            count = self.questions.filter(module=module).count()
            distribution.append({
                'module': module.name,
                'module_number': module.number,
                'count': count,
                'expected_weightage': float(module.weightage),
            })
        
        # Add unclassified
        unclassified = self.questions.filter(module__isnull=True).count()
        if unclassified:
            distribution.append({
                'module': 'Unclassified',
                'module_number': 0,
                'count': unclassified,
                'expected_weightage': 0,
            })
        
        return distribution
    
    def get_difficulty_distribution(self) -> Dict[str, int]:
        """Get question distribution by difficulty."""
        return dict(
            self.questions
            .exclude(difficulty='')
            .values('difficulty')
            .annotate(count=Count('id'))
            .values_list('difficulty', 'count')
        )
    
    def get_bloom_distribution(self) -> Dict[str, int]:
        """Get question distribution by Bloom's level."""
        return dict(
            self.questions
            .exclude(bloom_level='')
            .values('bloom_level')
            .annotate(count=Count('id'))
            .values_list('bloom_level', 'count')
        )
    
    def get_year_trend(self) -> List[Dict[str, Any]]:
        """Get question count trend by year."""
        papers = self.subject.papers.exclude(year='').order_by('year')
        trend = []
        
        for paper in papers:
            count = paper.questions.count()
            trend.append({
                'year': paper.year,
                'paper': paper.title,
                'question_count': count,
            })
        
        return trend
    
    def get_topic_frequency(self, top_n: int = 10) -> List[Dict[str, int]]:
        """Get most frequent topics."""
        all_topics = []
        for question in self.questions.exclude(topics=[]):
            all_topics.extend(question.topics)
        
        counter = Counter(all_topics)
        return [{'topic': t, 'count': c} for t, c in counter.most_common(top_n)]
    
    def get_topic_clusters_by_module(self, module_number: int = None) -> List[Dict[str, Any]]:
        """
        Get topic clusters with priority information.
        
        Args:
            module_number: Optional module number to filter by
            
        Returns:
            List of topic cluster data
        """
        clusters = TopicCluster.objects.filter(subject=self.subject)
        
        if module_number:
            clusters = clusters.filter(module__number=module_number)
        
        clusters = clusters.select_related('module').order_by(
            'module__number',
            'priority_tier',
            '-frequency_count'
        )
        
        results = []
        for cluster in clusters:
            results.append({
                'id': str(cluster.id),
                'module_number': cluster.module.number,
                'module_name': cluster.module.name,
                'topic_name': cluster.topic_name,
                'frequency_count': cluster.frequency_count,
                'years_appeared': cluster.years_appeared,
                'priority_tier': cluster.priority_tier,
                'priority_label': cluster.get_priority_tier_display() if cluster.priority_tier else 'Unknown',
                'total_marks': cluster.total_marks,
                'avg_marks': round(cluster.avg_marks, 1),
            })
        
        return results
    
    def get_priority_distribution(self) -> Dict[str, int]:
        """Get distribution of topics by priority tier."""
        distribution = {
            'tier_1': 0,
            'tier_2': 0,
            'tier_3': 0,
            'tier_4': 0,
        }
        
        clusters = TopicCluster.objects.filter(subject=self.subject)
        
        for cluster in clusters:
            if cluster.priority_tier == 1:
                distribution['tier_1'] += 1
            elif cluster.priority_tier == 2:
                distribution['tier_2'] += 1
            elif cluster.priority_tier == 3:
                distribution['tier_3'] += 1
            elif cluster.priority_tier == 4:
                distribution['tier_4'] += 1
        
        return distribution
    
    def get_top_topics_by_module(self, top_n: int = 3) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get top N topics per module based on frequency and marks.
        
        Args:
            top_n: Number of top topics to get per module
            
        Returns:
            Dict mapping module_number -> list of top topics
        """
        modules = self.subject.modules.all()
        results = {}
        
        for module in modules:
            clusters = TopicCluster.objects.filter(
                subject=self.subject,
                module=module
            ).order_by('-frequency_count', '-total_marks')[:top_n]
            
            topics = []
            for cluster in clusters:
                topics.append({
                    'topic_name': cluster.topic_name,
                    'frequency': cluster.frequency_count,
                    'years': cluster.years_appeared,
                    'priority_tier': cluster.priority_tier,
                    'total_marks': cluster.total_marks,
                })
            
            results[module.number] = topics
        
        return results
    
    def get_complete_stats(self) -> Dict[str, Any]:
        """Get all statistics including topic clusters."""
        return {
            'overview': self.get_overview(),
            'module_distribution': self.get_module_distribution(),
            'difficulty_distribution': self.get_difficulty_distribution(),
            'bloom_distribution': self.get_bloom_distribution(),
            'year_trend': self.get_year_trend(),
            'top_topics': self.get_topic_frequency(),
            'topic_clusters': self.get_topic_clusters_by_module(),
            'priority_distribution': self.get_priority_distribution(),
            'top_topics_by_module': self.get_top_topics_by_module(),
        }
    
    def cache_analytics(self) -> SubjectAnalytics:
        """
        Calculate and cache analytics for the subject.
        
        Returns:
            SubjectAnalytics instance
        """
        stats = self.get_complete_stats()
        
        # Get or create analytics object
        analytics, created = SubjectAnalytics.objects.get_or_create(
            subject=self.subject
        )
        
        # Update fields
        analytics.total_questions = stats['overview']['total_questions']
        analytics.unique_topics = TopicCluster.objects.filter(subject=self.subject).count()
        analytics.papers_analyzed = stats['overview']['papers_count']
        
        # Priority distribution
        priority_dist = stats['priority_distribution']
        analytics.tier_1_topics = priority_dist.get('tier_1', 0)
        analytics.tier_2_topics = priority_dist.get('tier_2', 0)
        analytics.tier_3_topics = priority_dist.get('tier_3', 0)
        analytics.tier_4_topics = priority_dist.get('tier_4', 0)
        
        # Top topics by module
        analytics.top_topics_by_module = stats['top_topics_by_module']
        
        # Module question counts
        module_counts = {}
        for dist in stats['module_distribution']:
            module_counts[dist['module']] = dist['count']
        analytics.module_question_counts = module_counts
        
        # Years covered
        years = set()
        for paper in self.subject.papers.all():
            if paper.year:
                years.add(paper.year)
        analytics.years_covered = sorted(list(years))
        
        analytics.save()
        return analytics
