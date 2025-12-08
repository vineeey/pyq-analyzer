"""
Analysis pipeline - Orchestrates the entire analysis workflow.
"""
import logging
from typing import Optional
from django.utils import timezone

from apps.papers.models import Paper
from apps.questions.models import Question
from .models import AnalysisJob
from .services.extractor import QuestionExtractor
from .services.classifier import ModuleClassifier
from .services.embedder import EmbeddingService
from .services.similarity import SimilarityService
from .services.bloom import BloomClassifier
from .services.difficulty import DifficultyEstimator

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the complete question analysis workflow."""
    
    def __init__(self, llm_client=None):
        self.extractor = QuestionExtractor()
        self.embedder = EmbeddingService()
        self.similarity = SimilarityService()
        self.bloom_classifier = BloomClassifier(llm_client)
        self.difficulty_estimator = DifficultyEstimator(llm_client)
        self.module_classifier = ModuleClassifier(llm_client)  # Works without LLM now
    
    def analyze_paper(self, paper: Paper) -> AnalysisJob:
        """
        Run complete analysis on a paper.
        
        Args:
            paper: Paper instance to analyze
            
        Returns:
            AnalysisJob with results
        """
        # Create analysis job
        job = AnalysisJob.objects.create(paper=paper)
        job.started_at = timezone.now()
        job.save()
        
        try:
            # Step 1: Extract text and questions
            job.status = AnalysisJob.Status.EXTRACTING
            job.progress = 10
            job.save()
            
            text = self.extractor.extract_text(paper.file.path)
            paper.raw_text = text
            paper.page_count = self.extractor.get_page_count(paper.file.path)
            paper.save()
            
            # Get exam pattern from subject
            exam_pattern = paper.subject.get_exam_pattern()
            questions_data = self.extractor.extract_questions(text, exam_pattern)
            job.questions_extracted = len(questions_data)
            job.progress = 30
            job.save()
            
            # Step 2: Create question objects and classify
            job.status = AnalysisJob.Status.CLASSIFYING
            job.save()
            
            subject = paper.subject
            modules = list(subject.modules.all())
            
            # First create all questions without classification
            created_questions = []
            for i, q_data in enumerate(questions_data):
                question = Question.objects.create(
                    paper=paper,
                    question_number=q_data['question_number'],
                    text=q_data['text'],
                    marks=q_data.get('marks')
                )
                
                # Check for module hint from PDF first
                module_hint = q_data.get('module_hint')
                if module_hint and modules:
                    try:
                        hint_num = int(module_hint)
                        module = next((m for m in modules if m.number == hint_num), None)
                        if module:
                            question.module = module
                    except (ValueError, TypeError):
                        pass
                
                # Bloom's taxonomy (rule-based, fast)
                question.bloom_level = self.bloom_classifier.classify(q_data['text'])
                
                # Difficulty (rule-based, fast)
                question.difficulty = self.difficulty_estimator.estimate(
                    q_data['text'], q_data.get('marks')
                )
                
                question.save()
                created_questions.append((question, q_data))
            
            job.progress = 40
            job.save()
            
            # Batch classify questions without module hints
            unclassified = [(q, data) for q, data in created_questions if q.module is None]
            if unclassified and modules and self.module_classifier:
                question_texts = [data['text'] for _, data in unclassified]
                module_nums = self.module_classifier.classify_batch(question_texts, subject, modules)
                
                for (question, _), module_num in zip(unclassified, module_nums):
                    if module_num:
                        question.module = next(
                            (m for m in modules if m.number == module_num), None
                        )
                        question.save()
            
            job.questions_classified = len(questions_data)
            job.progress = 60
            job.save()
            
            # Extract just the Question objects
            question_objects = [q for q, _ in created_questions]
            
            # Step 3: Generate embeddings
            job.status = AnalysisJob.Status.EMBEDDING
            job.progress = 70
            job.save()
            
            texts = [q.text for q in question_objects]
            embeddings = self.embedder.get_embeddings_batch(texts)
            
            for question, embedding in zip(question_objects, embeddings):
                if embedding:
                    question.embedding = embedding
                    question.save()
            
            # Step 4: Detect duplicates
            job.status = AnalysisJob.Status.DETECTING
            job.progress = 85
            job.save()
            
            # Get all questions for this subject for duplicate detection
            all_subject_questions = Question.objects.filter(
                paper__subject=subject
            ).exclude(embedding__isnull=True)
            
            existing = [(str(q.id), q.embedding) for q in all_subject_questions]
            
            duplicates = self.similarity.batch_find_duplicates(existing)
            
            for q_id, dup_id, score in duplicates:
                try:
                    question = Question.objects.get(id=q_id)
                    question.is_duplicate = True
                    question.duplicate_of_id = dup_id
                    question.similarity_score = score
                    question.save()
                except Question.DoesNotExist:
                    pass
            
            job.duplicates_found = len(duplicates)
            
            # Complete
            job.status = AnalysisJob.Status.COMPLETED
            job.progress = 100
            job.completed_at = timezone.now()
            
            paper.status = Paper.ProcessingStatus.COMPLETED
            paper.processed_at = timezone.now()
            paper.save()
            
            # Trigger clustering asynchronously if django-q is available
            try:
                from django_q.tasks import async_task
                from apps.analytics.tasks import cluster_subject_topics
                async_task(cluster_subject_topics, str(subject.id))
                logger.info(f"Queued clustering task for subject {subject.id}")
            except ImportError:
                logger.warning("Django-Q not available, skipping async clustering")
            
        except Exception as e:
            logger.error(f"Analysis failed for paper {paper.id}: {e}")
            job.status = AnalysisJob.Status.FAILED
            job.error_message = str(e)
            
            paper.status = Paper.ProcessingStatus.FAILED
            paper.processing_error = str(e)
            paper.save()
        
        job.save()
        return job
