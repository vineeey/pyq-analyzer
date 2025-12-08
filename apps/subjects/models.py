"""
Subject and Module models.
"""
from django.db import models
from django.conf import settings
from apps.core.models import SoftDeleteModel


class Subject(SoftDeleteModel):
    """Subject model with customizable module configuration."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    
    # Syllabus file (optional)
    syllabus_file = models.FileField(
        upload_to='syllabi/',
        null=True,
        blank=True
    )
    
    # Additional metadata
    university = models.CharField(max_length=255, blank=True)
    exam_board = models.CharField(max_length=255, blank=True)
    year = models.CharField(max_length=50, blank=True)
    
    # Exam pattern configuration (stored as JSON)
    exam_pattern = models.JSONField(
        default=dict,
        blank=True,
        help_text='Question-to-module mapping pattern (e.g., KTU standard)'
    )
    
    # Priority tier thresholds
    tier_thresholds = models.JSONField(
        default=dict,
        blank=True,
        help_text='Thresholds for priority tiers (e.g., {"tier_1": 4, "tier_2": 3, "tier_3": 2})'
    )
    
    # Other settings stored as JSON
    settings = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        ordering = ['-created_at']
        unique_together = ['user', 'name', 'code']
    
    def __str__(self):
        if self.code:
            return f"{self.code} - {self.name}"
        return self.name
    
    def get_module_count(self):
        """Return the number of modules for this subject."""
        return self.modules.count()
    
    def get_paper_count(self):
        """Return the number of papers for this subject."""
        return self.papers.count() if hasattr(self, 'papers') else 0
    
    def get_exam_pattern(self):
        """Get exam pattern, returning default if not set."""
        if self.exam_pattern:
            return self.exam_pattern
        
        # Default to KTU standard pattern
        from .exam_patterns import KTU_STANDARD_PATTERN
        return KTU_STANDARD_PATTERN
    
    def set_exam_pattern(self, pattern_name=None, custom_pattern=None):
        """
        Set exam pattern for this subject.
        
        Args:
            pattern_name: Name of predefined pattern ('ktu_standard', 'generic_5_module', etc.)
            custom_pattern: Custom pattern dict (overrides pattern_name)
        """
        if custom_pattern:
            self.exam_pattern = custom_pattern
        elif pattern_name:
            from .exam_patterns import get_pattern_by_name
            self.exam_pattern = get_pattern_by_name(pattern_name)
        self.save(update_fields=['exam_pattern'])
    
    def get_tier_thresholds(self):
        """Get priority tier thresholds, returning defaults if not set."""
        if self.tier_thresholds:
            return self.tier_thresholds
        
        # Default thresholds
        return {
            'tier_1': 4,  # 4+ exams = Top Priority
            'tier_2': 3,  # 3 exams = High Priority
            'tier_3': 2,  # 2 exams = Medium Priority
        }


class Module(SoftDeleteModel):
    """Module within a subject."""
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='modules'
    )
    name = models.CharField(max_length=255)
    number = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    
    # Topics within the module
    topics = models.JSONField(default=list, blank=True)
    # Example: ["Topic 1", "Topic 2", "Topic 3"]
    
    # Keywords for classification
    keywords = models.JSONField(default=list, blank=True)
    # Example: ["keyword1", "keyword2"]
    
    # Weightage (for analysis)
    weightage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Expected weightage percentage in exams'
    )
    
    class Meta:
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'
        ordering = ['number']
        unique_together = ['subject', 'number']
    
    def __str__(self):
        return f"Module {self.number}: {self.name}"
    
    def get_topic_list(self):
        """Return topics as a list."""
        if isinstance(self.topics, list):
            return self.topics
        return []
    
    def add_topic(self, topic):
        """Add a topic to the module."""
        if topic not in self.topics:
            self.topics.append(topic)
            self.save(update_fields=['topics'])
    
    def remove_topic(self, topic):
        """Remove a topic from the module."""
        if topic in self.topics:
            self.topics.remove(topic)
            self.save(update_fields=['topics'])
