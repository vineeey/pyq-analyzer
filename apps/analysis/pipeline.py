"""
Enhanced analysis pipeline with dual classification system.
"""
import logging
from typing import Optional
from django.utils import timezone
from django.conf import settings

from apps.papers.models import Paper
from apps.questions.models import Question
from .models import AnalysisJob
from .services.pymupdf_extractor import PyMuPDFExtractor
from .services.extractor import QuestionExtractor
from .services.classifier import ModuleClassifier
from .services.ai_classifier import AIClassifier
from .services.embedder import EmbeddingService
from .services.similarity import SimilarityService
from .services.bloom import BloomClassifier
from .services.difficulty import DifficultyEstimator

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """
    Enhanced orchestration of analysis workflow with dual classification.
    - KTU: Rule-based mapping (strict)
    - Other: AI-based classification (LLM + embeddings + clustering)
    """
    
    def __init__(self, llm_client=None):
        # Extractors
        self.pymupdf_extractor = PyMuPDFExtractor()  # Primary extractor
        self.fallback_extractor = QuestionExtractor()  # Fallback
        
        # Services
        self.embedder = EmbeddingService()
        self.similarity = SimilarityService()
        self.bloom_classifier = BloomClassifier(llm_client)
        self.difficulty_estimator = DifficultyEstimator(llm_client)
        
        # Classifiers
        self.module_classifier = ModuleClassifier(llm_client)  # For KTU
        self.ai_classifier = AIClassifier(llm_client, self.embedder)  # For Others
        
        self.llm_client = llm_client
    
    def analyze_paper(self, paper: Paper) -> AnalysisJob:
        """
        Run complete analysis on a paper with dual classification support.
        
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
            subject = paper.subject
            is_ktu = subject.university_type == 'KTU' if hasattr(subject, 'university_type') else True
            
            logger.info(f"Starting analysis for {paper.title} - University: {subject.university_type if hasattr(subject, 'university_type') else 'KTU'}")
            
            # Step 1: Extract text, images, and questions using PyMuPDF
            job.status = AnalysisJob.Status.EXTRACTING
            job.progress = 10
            job.save()
            
            try:
                questions_data, images = self.pymupdf_extractor.extract_questions_with_images(
                    paper.file.path
                )
                
                # Store extracted text
                paper.raw_text = self.pymupdf_extractor.extract_text(paper.file.path)
                paper.page_count = self.pymupdf_extractor.get_page_count(paper.file.path)
                paper.save()
                
                logger.info(f"PyMuPDF: Extracted {len(questions_data)} questions and {len(images)} images")
                
            except Exception as e:
                logger.error(f"PyMuPDF extraction failed, using fallback: {e}")
                
                # Fallback to pdfplumber
                text = self.fallback_extractor.extract_text(paper.file.path)
                paper.raw_text = text
                paper.page_count = self.fallback_extractor.get_page_count(paper.file.path)
                paper.save()
                
                questions_data = self.fallback_extractor.extract_questions(text)
                images = []
            
            job.questions_extracted = len(questions_data)
            job.progress = 30
            job.save()
            
            # Step 2: Classify questions based on university type
            job.status = AnalysisJob.Status.CLASSIFYING
            job.save()
            
            modules = list(subject.modules.all())
            
            if is_ktu:
                # KTU: Use strict rule-based classification
                classified_questions = self._classify_ktu_questions(
                    questions_data, subject, modules
                )
            else:
                # Other Universities: Use AI-based classification
                syllabus_text = subject.syllabus_text if hasattr(subject, 'syllabus_text') else None
                classified_questions = self.ai_classifier.classify_questions_semantic(
                    questions_data, subject, syllabus_text
                )
            
            job.progress = 60
            job.save()
            
            # Step 3: Create question objects in database
            job.status = AnalysisJob.Status.ANALYZING
            job.save()
            
            created_questions = []
            for q_data in classified_questions:
                # Find module
                module = None
                if 'module_number' in q_data:
                    module = next(
                        (m for m in modules if m.number == q_data['module_number']), 
                        None
                    )
                
                # Create question
                question = Question.objects.create(
                    paper=paper,
                    question_number=q_data.get('question_number', ''),
                    text=q_data['text'],
                    marks=q_data.get('marks'),
                    part=q_data.get('part', ''),
                    module=module,
                    images=q_data.get('images', []),
                    question_type=q_data.get('question_type', ''),
                    difficulty=q_data.get('difficulty', ''),
                    bloom_level=q_data.get('bloom_level', ''),
                    embedding=q_data.get('embedding')
                )
                
                created_questions.append(question)
            
            job.progress = 90
            job.save()
            
            # Step 4: Mark paper as completed
            paper.status = Paper.ProcessingStatus.COMPLETED
            paper.processed_at = timezone.now()
            paper.save()
            
            # Complete job
            job.status = AnalysisJob.Status.COMPLETED
            job.progress = 100
            job.completed_at = timezone.now()
            job.save()
            
            logger.info(f"Analysis completed: {len(created_questions)} questions created")
            return job
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            
            # Mark as failed
            job.status = AnalysisJob.Status.FAILED
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            
            paper.status = Paper.ProcessingStatus.FAILED
            paper.processing_error = str(e)
            paper.save()
            
            raise
    
    def _classify_ktu_questions(
        self,
        questions_data: list,
        subject,
        modules: list
    ) -> list:
        """
        KTU-specific rule-based classification.
        Uses strict question number to module mapping.
        """
        logger.info("Using KTU rule-based classification")
        
        exam_pattern = None
        if hasattr(subject, 'exam_pattern'):
            exam_pattern = subject.exam_pattern
        
        classified = []
        
        for q_data in questions_data:
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
            # Get module assignment from pattern
            module_num = None
            part = q_data.get('part', '')
            
            if exam_pattern and part:
                module_num = exam_pattern.get_module_for_question(
                    q_data['question_number'], part
                )
            
            # Add module_number to data
            q_data['module_number'] = module_num if module_num else 1
            
            # Use rule-based Bloom and difficulty
            q_data['bloom_level'] = self.bloom_classifier.classify(q_data['text'])
            q_data['difficulty'] = self.difficulty_estimator.estimate(
                q_data['text'], q_data.get('marks')
            )
            
            # Simple question type classification
            q_data['question_type'] = self._simple_question_type(q_data['text'])
            
            classified.append(q_data)
        
        return classified
    
    def _simple_question_type(self, text: str) -> str:
        """Simple rule-based question type classification."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['define', 'what is']):
            return 'definition'
        elif any(word in text_lower for word in ['derive', 'proof']):
            return 'derivation'
        elif any(word in text_lower for word in ['calculate', 'compute']):
            return 'numerical'
        elif any(word in text_lower for word in ['draw', 'diagram']):
            return 'diagram'
        elif any(word in text_lower for word in ['compare', 'differentiate']):
            return 'comparison'
        else:
            return 'theory'

            
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
