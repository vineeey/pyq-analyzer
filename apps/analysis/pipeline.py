"""
Analysis pipeline - Orchestrates the entire analysis workflow.
"""
import logging
import re
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
    
    def _apply_ktu_rules(self, question_number: str, part: str) -> Optional[int]:
        """
        Apply KTU-specific classification rules.
        
        KTU Rules:
        - Qn 1 & 2 → Module 1
        - Qn 3 & 4 → Module 2
        - Qn 5 & 6 → Module 3
        - Qn 7 & 8 → Module 4
        - Qn 9 & 10 → Module 5
        - Qn 11 & 12 → Module 1
        - Qn 13 & 14 → Module 2
        - Qn 15 & 16 → Module 3
        - Qn 17 & 18 → Module 4
        - Qn 19 & 20 → Module 5
        """
        # Extract numeric part from question number (e.g., "11a" -> 11)
        match = re.match(r'(\d+)', str(question_number))
        if not match:
            return None
        
        q_num = int(match.group(1))
        
        # Apply KTU rules
        if q_num in [1, 2, 11, 12]:
            return 1
        elif q_num in [3, 4, 13, 14]:
            return 2
        elif q_num in [5, 6, 15, 16]:
            return 3
        elif q_num in [7, 8, 17, 18]:
            return 4
        elif q_num in [9, 10, 19, 20]:
            return 5
        
        return None
    
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
            
            questions_data = self.extractor.extract_questions(text)
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
                    marks=q_data.get('marks'),
                    part=q_data.get('part', '')  # Store Part A or B
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
                
                # For KTU papers, apply standard KTU classification rules
                if not question.module and paper.university == 'ktu':
                    module_num = self._apply_ktu_rules(q_data['question_number'], q_data.get('part', ''))
                    if module_num and modules:
                        module = next((m for m in modules if m.number == module_num), None)
                        if module:
                            question.module = module
                
                # If still no module, try using exam pattern if available
                if not question.module and hasattr(subject, 'exam_pattern'):
                    exam_pattern = subject.exam_pattern
                    part = q_data.get('part', '')
                    if exam_pattern and part:
                        module_num = exam_pattern.get_module_for_question(
                            q_data['question_number'], part
                        )
                        if module_num:
                            module = next((m for m in modules if m.number == module_num), None)
                            if module:
                                question.module = module
                
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
            
        except Exception as e:
            logger.error(f"Analysis failed for paper {paper.id}: {e}")
            job.status = AnalysisJob.Status.FAILED
            job.error_message = str(e)
            
            paper.status = Paper.ProcessingStatus.FAILED
            paper.processing_error = str(e)
            paper.save()
        
        job.save()
        return job
