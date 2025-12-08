"""
Question models with full analysis fields.
"""
from django.db import models
from apps.core.models import BaseModel


class Question(BaseModel):
    """Extracted question with all analysis fields."""
    
    class DifficultyLevel(models.TextChoices):
        EASY = 'easy', 'Easy'
        MEDIUM = 'medium', 'Medium'
        HARD = 'hard', 'Hard'
    
    class BloomLevel(models.TextChoices):
        REMEMBER = 'remember', 'Remember'
        UNDERSTAND = 'understand', 'Understand'
        APPLY = 'apply', 'Apply'
        ANALYZE = 'analyze', 'Analyze'
        EVALUATE = 'evaluate', 'Evaluate'
        CREATE = 'create', 'Create'
    
    # Source
    paper = models.ForeignKey(
        'papers.Paper',
        on_delete=models.CASCADE,
        related_name='questions'
    )
    
    # Question content
    question_number = models.CharField(max_length=20, blank=True)
    text = models.TextField()
    sub_questions = models.JSONField(default=list, blank=True)
    marks = models.PositiveIntegerField(null=True, blank=True)
    
    # Classification
    module = models.ForeignKey(
        'subjects.Module',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions'
    )
    topics = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    
    # Analysis results
    difficulty = models.CharField(
        max_length=10,
        choices=DifficultyLevel.choices,
        blank=True
    )
    bloom_level = models.CharField(
        max_length=15,
        choices=BloomLevel.choices,
        blank=True
    )
    
    # Embedding for similarity search
    embedding = models.JSONField(null=True, blank=True)  # Store as list of floats
    
    # Topic clustering
    topic_cluster = models.ForeignKey(
        'analytics.TopicCluster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions',
        help_text='Topic cluster this question belongs to'
    )
    normalized_text = models.TextField(
        blank=True,
        help_text='Normalized text for clustering/matching'
    )
    
    # Duplicate detection
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicates'
    )
    similarity_score = models.FloatField(null=True, blank=True)
    
    # Manual override flags
    module_manually_set = models.BooleanField(default=False)
    difficulty_manually_set = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        ordering = ['question_number']
    
    def __str__(self):
        return f"Q{self.question_number}: {self.text[:50]}..."
    
    def get_similar_questions(self, threshold=0.8):
        """Find similar questions based on embedding similarity."""
        if not self.embedding:
            return Question.objects.none()
        # This would be implemented using the embedding service
        return Question.objects.none()
