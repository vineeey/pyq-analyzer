"""
Analytics models for tracking topic clusters and repetitions.
"""
from django.db import models
from apps.core.models import BaseModel


class TopicCluster(BaseModel):
    """
    Represents a cluster of similar questions grouped as a single topic.
    Tracks repetition across years for priority assignment.
    """
    
    class PriorityTier(models.IntegerChoices):
        TIER_4 = 4, 'Low Priority (1 exam)'
        TIER_3 = 3, 'Medium Priority (2 exams)'
        TIER_2 = 2, 'High Priority (3 exams)'
        TIER_1 = 1, 'Top Priority (4+ exams)'
    
    subject = models.ForeignKey(
        'subjects.Subject',
        on_delete=models.CASCADE,
        related_name='topic_clusters'
    )
    module = models.ForeignKey(
        'subjects.Module',
        on_delete=models.CASCADE,
        related_name='topic_clusters'
    )
    
    # Topic identification
    topic_name = models.CharField(
        max_length=500,
        help_text='Human-readable topic name'
    )
    normalized_key = models.CharField(
        max_length=500,
        help_text='Normalized text for matching',
        db_index=True
    )
    
    # Repetition tracking
    frequency_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of times this topic appears across all papers'
    )
    years_appeared = models.JSONField(
        default=list,
        blank=True,
        help_text='List of years when this topic appeared'
    )
    papers_appeared = models.JSONField(
        default=list,
        blank=True,
        help_text='List of paper IDs where this topic appeared'
    )
    
    # Priority assignment
    priority_tier = models.IntegerField(
        choices=PriorityTier.choices,
        null=True,
        blank=True,
        help_text='Priority tier based on frequency'
    )
    
    # Marks statistics
    total_marks = models.PositiveIntegerField(
        default=0,
        help_text='Total marks across all occurrences'
    )
    avg_marks = models.FloatField(
        default=0.0,
        help_text='Average marks per question'
    )
    
    # Sample questions
    representative_question = models.TextField(
        blank=True,
        help_text='Representative question text for this topic'
    )
    
    # Clustering metadata
    embedding_centroid = models.JSONField(
        null=True,
        blank=True,
        help_text='Average embedding vector for this cluster'
    )
    
    class Meta:
        verbose_name = 'Topic Cluster'
        verbose_name_plural = 'Topic Clusters'
        ordering = ['module__number', '-frequency_count', 'topic_name']
        unique_together = ['subject', 'module', 'normalized_key']
    
    def __str__(self):
        return f"Module {self.module.number}: {self.topic_name} ({self.frequency_count}x)"
    
    def update_priority_tier(self, tier_thresholds=None):
        """
        Update priority tier based on frequency count.
        
        Args:
            tier_thresholds: Dict with keys 'tier_1', 'tier_2', 'tier_3' defining min frequencies
        """
        if tier_thresholds is None:
            tier_thresholds = {
                'tier_1': 4,  # 4+ exams = Top Priority
                'tier_2': 3,  # 3 exams = High Priority
                'tier_3': 2,  # 2 exams = Medium Priority
            }
        
        if self.frequency_count >= tier_thresholds.get('tier_1', 4):
            self.priority_tier = self.PriorityTier.TIER_1
        elif self.frequency_count >= tier_thresholds.get('tier_2', 3):
            self.priority_tier = self.PriorityTier.TIER_2
        elif self.frequency_count >= tier_thresholds.get('tier_3', 2):
            self.priority_tier = self.PriorityTier.TIER_3
        else:
            self.priority_tier = self.PriorityTier.TIER_4
        
        self.save(update_fields=['priority_tier'])
    
    def add_occurrence(self, question, year=None):
        """
        Add a question occurrence to this cluster.
        
        Args:
            question: Question instance
            year: Year string (optional, will be extracted from paper if not provided)
        """
        if not year and question.paper:
            year = question.paper.year
        
        # Update frequency
        self.frequency_count += 1
        
        # Update years list
        if year and year not in self.years_appeared:
            years = self.years_appeared if isinstance(self.years_appeared, list) else []
            years.append(year)
            self.years_appeared = sorted(years)
        
        # Update papers list
        paper_id = str(question.paper.id) if question.paper else None
        if paper_id:
            papers = self.papers_appeared if isinstance(self.papers_appeared, list) else []
            if paper_id not in papers:
                papers.append(paper_id)
                self.papers_appeared = papers
        
        # Update marks
        if question.marks:
            self.total_marks += question.marks
            self.avg_marks = self.total_marks / self.frequency_count
        
        # Update representative question if empty or this one is better
        if not self.representative_question or len(question.text) > len(self.representative_question):
            self.representative_question = question.text[:500]
        
        self.save()


class SubjectAnalytics(BaseModel):
    """
    Cached analytics summary for a subject.
    Regenerated when papers are added or analysis is run.
    """
    
    subject = models.OneToOneField(
        'subjects.Subject',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Overall statistics
    total_questions = models.PositiveIntegerField(default=0)
    unique_topics = models.PositiveIntegerField(default=0)
    papers_analyzed = models.PositiveIntegerField(default=0)
    
    # Priority distribution
    tier_1_topics = models.PositiveIntegerField(
        default=0,
        help_text='Number of top priority topics'
    )
    tier_2_topics = models.PositiveIntegerField(
        default=0,
        help_text='Number of high priority topics'
    )
    tier_3_topics = models.PositiveIntegerField(
        default=0,
        help_text='Number of medium priority topics'
    )
    tier_4_topics = models.PositiveIntegerField(
        default=0,
        help_text='Number of low priority topics'
    )
    
    # Top topics per module (for dashboard)
    top_topics_by_module = models.JSONField(
        default=dict,
        blank=True,
        help_text='Top 3 topics per module with their stats'
    )
    
    # Module-wise statistics
    module_question_counts = models.JSONField(
        default=dict,
        blank=True,
        help_text='Question counts per module'
    )
    
    # Year coverage
    years_covered = models.JSONField(
        default=list,
        blank=True,
        help_text='List of years with analyzed papers'
    )
    
    last_analyzed = models.DateTimeField(
        auto_now=True,
        help_text='Last time analytics were computed'
    )
    
    class Meta:
        verbose_name = 'Subject Analytics'
        verbose_name_plural = 'Subject Analytics'
    
    def __str__(self):
        return f"Analytics for {self.subject.name}"
