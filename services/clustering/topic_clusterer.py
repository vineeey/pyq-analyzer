"""
Topic clustering service using embeddings and similarity matching.
"""
import logging
import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from django.db.models import Q

from apps.questions.models import Question
from apps.analytics.models import TopicCluster
from apps.subjects.models import Subject, Module
from .normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class TopicClusterer:
    """
    Clusters similar questions into topics across multiple papers.
    Uses embeddings + fuzzy matching for robust clustering.
    """
    
    def __init__(self, similarity_threshold: float = 0.75):
        """
        Initialize clusterer.
        
        Args:
            similarity_threshold: Cosine similarity threshold for clustering (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
        self.normalizer = TextNormalizer()
    
    def cluster_subject_questions(self, subject: Subject) -> Dict[int, List[TopicCluster]]:
        """
        Cluster all questions for a subject by module.
        
        Args:
            subject: Subject instance
            
        Returns:
            Dict mapping module_number -> list of TopicClusters
        """
        logger.info(f"Starting clustering for subject: {subject.name}")
        
        # Get all questions for this subject
        questions = Question.objects.filter(
            paper__subject=subject,
            module__isnull=False
        ).select_related('paper', 'module').order_by('module__number', 'paper__year')
        
        if not questions.exists():
            logger.warning(f"No questions found for subject {subject.id}")
            return {}
        
        # Clear existing clusters for this subject
        TopicCluster.objects.filter(subject=subject).delete()
        
        # Group questions by module
        questions_by_module = {}
        for question in questions:
            module_num = question.module.number
            if module_num not in questions_by_module:
                questions_by_module[module_num] = []
            questions_by_module[module_num].append(question)
        
        # Cluster each module separately
        results = {}
        for module_num, module_questions in questions_by_module.items():
            logger.info(f"Clustering {len(module_questions)} questions for Module {module_num}")
            clusters = self._cluster_module_questions(
                subject,
                module_questions[0].module,
                module_questions
            )
            results[module_num] = clusters
        
        logger.info(f"Clustering complete. Created {sum(len(c) for c in results.values())} clusters")
        return results
    
    def _cluster_module_questions(
        self,
        subject: Subject,
        module: Module,
        questions: List[Question]
    ) -> List[TopicCluster]:
        """
        Cluster questions within a single module.
        
        Args:
            subject: Subject instance
            module: Module instance
            questions: List of questions for this module
            
        Returns:
            List of created TopicCluster objects
        """
        if not questions:
            return []
        
        # Normalize all question texts
        for q in questions:
            if not q.normalized_text:
                q.normalized_text = self.normalizer.normalize(q.text)
                q.save(update_fields=['normalized_text'])
        
        # Build similarity matrix using embeddings if available
        clusters = []
        assigned = set()
        
        for i, q1 in enumerate(questions):
            if q1.id in assigned:
                continue
            
            # Start new cluster with this question
            cluster_questions = [q1]
            assigned.add(q1.id)
            
            # Find similar questions
            for j in range(i + 1, len(questions)):
                q2 = questions[j]
                if q2.id in assigned:
                    continue
                
                similarity = self._calculate_similarity(q1, q2)
                
                if similarity >= self.similarity_threshold:
                    cluster_questions.append(q2)
                    assigned.add(q2.id)
            
            # Create topic cluster
            if cluster_questions:
                cluster = self._create_topic_cluster(
                    subject,
                    module,
                    cluster_questions
                )
                if cluster:
                    clusters.append(cluster)
        
        return clusters
    
    def _calculate_similarity(self, q1: Question, q2: Question) -> float:
        """
        Calculate similarity between two questions.
        Uses embeddings if available, falls back to text matching.
        
        Args:
            q1: First question
            q2: Second question
            
        Returns:
            Similarity score (0.0-1.0)
        """
        # Try embedding-based similarity first
        if q1.embedding and q2.embedding:
            try:
                emb1 = np.array(q1.embedding)
                emb2 = np.array(q2.embedding)
                
                # Cosine similarity
                dot_product = np.dot(emb1, emb2)
                norm1 = np.linalg.norm(emb1)
                norm2 = np.linalg.norm(emb2)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    return max(0.0, min(1.0, similarity))
            except Exception as e:
                logger.warning(f"Embedding similarity calculation failed: {e}")
        
        # Fallback to normalized text similarity
        return self._text_similarity(q1.normalized_text, q2.normalized_text)
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using Jaccard similarity on words.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_topic_cluster(
        self,
        subject: Subject,
        module: Module,
        questions: List[Question]
    ) -> Optional[TopicCluster]:
        """
        Create a TopicCluster from a list of similar questions.
        
        Args:
            subject: Subject instance
            module: Module instance
            questions: List of similar questions
            
        Returns:
            Created TopicCluster or None
        """
        if not questions:
            return None
        
        # Generate topic name from representative question
        representative = max(questions, key=lambda q: len(q.text))
        topic_name = self._generate_topic_name(representative.text)
        
        # Create normalized key
        normalized_key = self.normalizer.create_topic_key(representative.text)
        
        # Calculate statistics
        years = set()
        paper_ids = set()
        total_marks = 0
        
        for q in questions:
            if q.paper and q.paper.year:
                years.add(q.paper.year)
            if q.paper:
                paper_ids.add(str(q.paper.id))
            if q.marks:
                total_marks += q.marks
        
        frequency = len(questions)
        avg_marks = total_marks / frequency if frequency > 0 else 0
        
        # Calculate centroid embedding if embeddings available
        centroid = None
        embeddings = [q.embedding for q in questions if q.embedding]
        if embeddings:
            try:
                centroid = np.mean(embeddings, axis=0).tolist()
            except Exception as e:
                logger.warning(f"Failed to calculate centroid: {e}")
        
        # Create cluster
        try:
            cluster = TopicCluster.objects.create(
                subject=subject,
                module=module,
                topic_name=topic_name,
                normalized_key=normalized_key,
                frequency_count=frequency,
                years_appeared=sorted(list(years)),
                papers_appeared=list(paper_ids),
                total_marks=total_marks,
                avg_marks=avg_marks,
                representative_question=representative.text[:500],
                embedding_centroid=centroid
            )
            
            # Update priority tier
            tier_thresholds = subject.get_tier_thresholds()
            cluster.update_priority_tier(tier_thresholds)
            
            # Link questions to cluster
            for q in questions:
                q.topic_cluster = cluster
                q.save(update_fields=['topic_cluster'])
            
            return cluster
        
        except Exception as e:
            logger.error(f"Failed to create topic cluster: {e}")
            return None
    
    def _generate_topic_name(self, question_text: str, max_length: int = 100) -> str:
        """
        Generate a concise topic name from question text.
        
        Args:
            question_text: Full question text
            max_length: Maximum length of topic name
            
        Returns:
            Topic name
        """
        # Remove common question starters
        text = question_text
        
        prefixes = [
            r'^(What|Which|Who|When|Where|Why|How)\s+(is|are|was|were|do|does|did)\s+',
            r'^(Explain|Describe|Define|Discuss|Illustrate|List|Mention|State)\s+',
            r'^\d+[a-z]?\.\s*',
            r'^\d+[a-z]?\)\s*',
        ]
        
        for prefix in prefixes:
            text = re.sub(prefix, '', text, flags=re.IGNORECASE)
        
        # Take first sentence or first N characters
        sentences = text.split('.')
        if sentences:
            topic = sentences[0].strip()
        else:
            topic = text[:max_length].strip()
        
        # Limit length
        if len(topic) > max_length:
            topic = topic[:max_length].rsplit(' ', 1)[0] + '...'
        
        return topic if topic else question_text[:max_length]
    
    def update_cluster_priorities(self, subject: Subject):
        """
        Update priority tiers for all clusters in a subject.
        
        Args:
            subject: Subject instance
        """
        tier_thresholds = subject.get_tier_thresholds()
        clusters = TopicCluster.objects.filter(subject=subject)
        
        for cluster in clusters:
            cluster.update_priority_tier(tier_thresholds)
        
        logger.info(f"Updated priorities for {clusters.count()} clusters")
