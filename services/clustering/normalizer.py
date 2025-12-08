"""
Text normalization for question clustering.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)


class TextNormalizer:
    """Normalizes question text for clustering and comparison."""
    
    # Common words to remove (stopwords specific to exam questions)
    STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could', 'will',
        'would', 'should', 'may', 'might', 'must', 'shall',
        # Question-specific stopwords
        'what', 'which', 'who', 'whom', 'whose', 'when', 'where', 'why', 'how',
        'explain', 'describe', 'define', 'discuss', 'illustrate', 'list',
        'mention', 'state', 'give', 'write', 'short', 'note', 'notes',
        'briefly', 'detail', 'details', 'answer', 'following', 'briefly',
    }
    
    # Patterns to remove
    REMOVE_PATTERNS = [
        r'\d{4}',  # Years (2021, 2022, etc.)
        r'\(\d+\s*marks?\)',  # (3 marks), (14 marks)
        r'\d+\s*marks?',  # 3 marks, 14 marks
        r'Q\d+[a-z]?',  # Q1, Q11a, etc.
        r'Question\s*\d+',  # Question 1, etc.
        r'\(Dec|June|Nov|May|Apr|Jan|Feb|Mar|Aug|Sep|Oct\s*\d{4}\)',  # Month/Year
        r'\[[^\]]+\]',  # Anything in square brackets
    ]
    
    def __init__(self):
        self.stopwords = self.STOPWORDS
    
    def normalize(self, text: str) -> str:
        """
        Normalize text for clustering.
        
        Args:
            text: Raw question text
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove year references and marks
        for pattern in self.REMOVE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove special characters except spaces and basic punctuation
        text = re.sub(r'[^\w\s\.\,\-]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove stopwords
        words = text.split()
        words = [w for w in words if w not in self.stopwords and len(w) > 2]
        
        # Rejoin
        normalized = ' '.join(words)
        
        # Remove leading/trailing whitespace
        normalized = normalized.strip()
        
        return normalized
    
    def normalize_batch(self, texts: List[str]) -> List[str]:
        """Normalize multiple texts."""
        return [self.normalize(text) for text in texts]
    
    def extract_key_phrases(self, text: str, max_phrases: int = 5) -> List[str]:
        """
        Extract key phrases from question text.
        
        Args:
            text: Normalized or raw text
            max_phrases: Maximum number of phrases to extract
            
        Returns:
            List of key phrases
        """
        # Normalize first
        normalized = self.normalize(text) if not self._is_normalized(text) else text
        
        # Split into words
        words = normalized.split()
        
        # Extract n-grams (2-3 words)
        phrases = []
        
        # Bigrams
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            phrases.append(phrase)
        
        # Trigrams
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            phrases.append(phrase)
        
        # Take most common/longest
        phrases = sorted(set(phrases), key=len, reverse=True)
        
        return phrases[:max_phrases]
    
    def _is_normalized(self, text: str) -> bool:
        """Check if text appears to be already normalized."""
        # Simple heuristic: if all lowercase and no years/marks
        return (text == text.lower() and
                not re.search(r'\d{4}', text) and
                not re.search(r'\d+\s*marks?', text, re.IGNORECASE))
    
    def create_topic_key(self, text: str) -> str:
        """
        Create a concise topic key from question text.
        Used as a lookup key for clustering.
        
        Args:
            text: Question text
            
        Returns:
            Topic key (first 50 chars of normalized text)
        """
        normalized = self.normalize(text)
        # Take first 50 characters
        key = normalized[:50].strip()
        return key if key else normalized[:100].strip()
