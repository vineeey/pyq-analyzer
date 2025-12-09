"""
PDF text extraction service.
"""
import logging
import re
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class QuestionExtractor:
    """Extracts questions from PDF files."""
    
    def __init__(self):
        self.pdfplumber = None
        self.fitz = None
        self._load_libraries()
    
    def _load_libraries(self):
        """Lazy load PDF processing libraries."""
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
        except ImportError:
            logger.warning("pdfplumber not available")
        
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
        except ImportError:
            logger.warning("PyMuPDF not available")
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract all text from a PDF file."""
        text_parts = []
        
        if self.pdfplumber:
            try:
                with self.pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
            except Exception as e:
                logger.error(f"pdfplumber extraction failed: {e}")
        
        # Fallback to PyMuPDF
        if not text_parts and self.fitz:
            try:
                doc = self.fitz.open(pdf_path)
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
            except Exception as e:
                logger.error(f"PyMuPDF extraction failed: {e}")
        
        return '\n'.join(text_parts)
    
    def extract_questions(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse text to extract individual questions from university question papers.
        
        Handles KTU-style exam paper formats with OCR artifacts.
        """
        questions = []
        
        # First, clean and preprocess the text
        cleaned_text = self._clean_text(text)
        logger.debug(f"Cleaned text length: {len(cleaned_text)} characters")
        
        # Extract Part A questions (1-10, typically 3 marks each)
        part_a_questions = self._extract_part_a(cleaned_text)
        logger.info(f"Extracted {len(part_a_questions)} Part A questions")
        questions.extend(part_a_questions)
        
        # Extract Part B questions (11-20, module-wise, typically 6-8 marks each)
        part_b_questions = self._extract_part_b(cleaned_text)
        logger.info(f"Extracted {len(part_b_questions)} Part B questions")
        questions.extend(part_b_questions)
        
        # If extraction yielded very few questions, try fallback
        if len(questions) < 5:
            logger.warning(f"Primary extraction yielded only {len(questions)} questions, trying fallback method...")
            questions = self._fallback_extraction(cleaned_text)
            logger.info(f"Fallback extraction found {len(questions)} questions")
        
        # Deduplicate
        questions = self._deduplicate(questions)
        
        logger.info(f"Final: Extracted {len(questions)} unique questions (Part A: {sum(1 for q in questions if q.get('part') == 'A')}, Part B: {sum(1 for q in questions if q.get('part') == 'B')})")
        return questions
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text from PDF."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip common header/footer patterns
            skip_patterns = [
                r'^\d{10,}$',  # Registration numbers
                r'^Page\s*\d+',
                r'^Name:',
                r'^\$#\d+',
                r'^APJ ABDUL KALAM',
                r'^B\.?Tech\s+Degree',
                r'^Course\s*(Code|Name):',
                r'^Max\.?\s*Marks',
                r'^Duration:',
                r'^\d+\s+of\s+\d+',
                r'^[.,;:\-\s]+$',  # Just punctuation
            ]
            
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    skip = True
                    break
            
            if not skip:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_part_a(self, text: str) -> List[Dict[str, Any]]:
        """Extract Part A (short answer) questions."""
        questions = []
        
        # Find Part A section
        part_a_match = re.search(
            r'PART\s*A(.*?)(?:PART\s*B|Module\s*[-–:]?\s*[1IVX])',
            text, re.IGNORECASE | re.DOTALL
        )
        
        if not part_a_match:
            logger.debug("No Part A section found in document")
            return questions
        
        part_a_text = part_a_match.group(1)
        logger.debug(f"Found Part A section with {len(part_a_text)} characters")
        
        # Clean instruction text
        part_a_text = re.sub(r'\(Answer.*?\)', '', part_a_text, flags=re.IGNORECASE)
        part_a_text = re.sub(r'each\s+question\s+carries.*', '', part_a_text, flags=re.IGNORECASE)
        
        # Fix common OCR errors
        part_a_text = re.sub(r'\bI\s+(What|How|Explain|Define|List)', r'1 \1', part_a_text)
        part_a_text = re.sub(r'\bl0\b', '10', part_a_text)
        
        # Join lines into continuous text for easier pattern matching
        part_a_text = ' '.join(part_a_text.split())
        
        # Pattern to match questions: number followed by question text
        # More flexible pattern to catch various formats:
        # - "1. What is..." or "1) What is..." or "1 What is..."
        # - Handles questions starting with capital letters, all caps, or lowercase (after punctuation)
        
        # Find all question starts - more flexible pattern
        # Matches: digit(s) optionally followed by . or ) then whitespace and a letter
        q_starts = list(re.finditer(r'(\d{1,2})[\.\)]*\s+([A-Za-z])', part_a_text))
        
        for i, match in enumerate(q_starts):
            q_num = match.group(1)
            
            # Skip if number > 10 (Part A typically has Q1-Q10)
            try:
                if int(q_num) > 10:
                    continue
            except ValueError:
                continue
            
            # Get text until next question or end
            start = match.start()
            if i + 1 < len(q_starts):
                end = q_starts[i + 1].start()
            else:
                end = len(part_a_text)
            
            q_text = part_a_text[start:end].strip()
            
            # Remove the question number and punctuation from start
            q_text = re.sub(r'^\d{1,2}[\.\)]*\s+', '', q_text)
            
            # Extract marks if present (typically at end like "3 marks" or "(3)")
            marks = 3  # Default for Part A
            marks_match = re.search(r'\(?\s*(\d{1,2})\s*marks?\)?\s*$', q_text, re.IGNORECASE)
            if marks_match:
                try:
                    marks = int(marks_match.group(1))
                    q_text = q_text[:marks_match.start()].strip()
                except ValueError:
                    pass
            
            # Remove trailing marks without the word "marks"
            q_text = re.sub(r'\s+\(?\d{1,2}\)?\s*$', '', q_text)
            
            # Clean OCR artifacts that sometimes appear at end
            q_text = re.sub(
                r'\s+(causes|depletion|hazards|assessments|disasters|management|reduction|examples|country)\s*\.?\s*$',
                '', q_text, flags=re.IGNORECASE
            )
            
            q_text = q_text.strip()
            
            # Accept question if it's reasonably long and starts with a letter
            if len(q_text) >= 10 and re.match(r'^[A-Za-z]', q_text):
                questions.append({
                    'question_number': q_num,
                    'text': q_text,
                    'marks': marks,
                    'part': 'A',
                    'module_hint': None,
                })
        
        return questions
    
    def _extract_part_b(self, text: str) -> List[Dict[str, Any]]:
        """Extract Part B (long answer, module-wise) questions."""
        questions = []
        roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}
        
        # Split by module markers
        # Pattern handles: "Module -1", "Module-1", "Module 1", "Module -I", etc.
        module_pattern = r'Module\s*[-–:]?\s*(\d+|[IVX]+)'
        parts = re.split(module_pattern, text, flags=re.IGNORECASE)
        
        # parts[0] is before first module, then alternating: mod_num, content, mod_num, content...
        for i in range(1, len(parts), 2):
            if i + 1 >= len(parts):
                break
            
            mod_str = parts[i].strip()
            mod_content = parts[i + 1]
            
            # Convert module number
            if mod_str.upper() in roman_map:
                mod_num = roman_map[mod_str.upper()]
            else:
                try:
                    mod_num = int(mod_str)
                except ValueError:
                    continue
            
            # Stop content at next PART marker if present
            next_part = re.search(r'PART\s*[A-Z]', mod_content, re.IGNORECASE)
            if next_part:
                mod_content = mod_content[:next_part.start()]
            
            # Fix common OCR errors in question numbers
            mod_content = re.sub(r'\bl(\d)', r'1\1', mod_content)  # l3 -> 13
            mod_content = re.sub(r'\bI\s*E\b', '18', mod_content)  # I E -> 18
            
            # Join lines
            mod_content = ' '.join(mod_content.split())
            
            # Extract sub-questions with more flexible pattern
            # Handles: "11a)", "11 a)", "11. a)", "11a )", "(a)", etc.
            # Updated pattern to be more lenient and catch more variations
            sub_q_pattern = r'(\d{1,2})\s*[\.\)]*\s*([a-z])\s*[\.\)]*\s+([A-Za-z][^0-9]*?)(?=\s+\d{1,2}\s*[\.\)]*\s*[a-z]|$)'
            
            for match in re.finditer(sub_q_pattern, mod_content, re.IGNORECASE):
                q_num = match.group(1)
                sub = match.group(2).lower()
                q_text = match.group(3).strip()
                
                # Clean text
                q_text = re.sub(r'\s+', ' ', q_text)
                
                # Extract marks from end (look for patterns like "7 marks", "(7)", "7")
                marks = None
                marks_match = re.search(r'\(?\s*(\d{1,2})\s*marks?\)?\s*$', q_text, re.IGNORECASE)
                if marks_match:
                    try:
                        m = int(marks_match.group(1))
                        if m <= 14:
                            marks = m
                            q_text = q_text[:marks_match.start()].strip()
                    except ValueError:
                        pass
                
                # Remove trailing single digit if no marks found yet
                if marks is None:
                    trailing_num = re.search(r'\s+(\d{1,2})\s*$', q_text)
                    if trailing_num:
                        m = int(trailing_num.group(1))
                        if m <= 14:
                            marks = m
                            q_text = q_text[:trailing_num.start()].strip()
                
                # Remove trailing garbage
                q_text = re.sub(r'\s*[E]\s*$', '', q_text)
                q_text = q_text.strip()
                
                # Accept question if reasonably long and starts with a letter
                if len(q_text) >= 10 and re.match(r'^[A-Za-z]', q_text):
                    questions.append({
                        'question_number': f"{q_num}{sub}",
                        'text': q_text,
                        'marks': marks if marks else 7,
                        'part': 'B',
                        'module_hint': mod_num,
                    })
        
        return questions
    
    def _fallback_extraction(self, text: str) -> List[Dict[str, Any]]:
        """
        Fallback extraction using simpler line-by-line approach.
        Used when primary extraction fails.
        """
        questions = []
        lines = text.split('\n')
        
        current_module = None
        roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}
        in_part_b = False
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Track PART
            if re.match(r'PART\s*B', line, re.IGNORECASE):
                in_part_b = True
            
            # Track Module
            mod_match = re.match(r'Module\s*[-–:]?\s*(\d+|[IVX]+)', line, re.IGNORECASE)
            if mod_match:
                mod_str = mod_match.group(1)
                if mod_str.upper() in roman_map:
                    current_module = roman_map[mod_str.upper()]
                else:
                    try:
                        current_module = int(mod_str)
                    except ValueError:
                        pass
                in_part_b = True
                i += 1
                continue
            
            # Look for question patterns - more flexible
            # Pattern: number [optional letter] [optional punctuation] text
            q_match = re.match(r'^(\d{1,2})\s*([a-z])?\s*[\.\)]*\s*(.+)', line, re.IGNORECASE)
            if q_match and q_match.group(3).strip():
                q_num = q_match.group(1)
                sub = q_match.group(2) or ''
                q_text = q_match.group(3).strip()
                
                # Skip if doesn't start with question-like text (letter)
                if not re.match(r'^[A-Za-z]', q_text):
                    i += 1
                    continue
                
                # Accumulate multi-line question text
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    
                    # Stop at new question, module, or part
                    if re.match(r'^(\d{1,2})\s*[a-z]?\s*\)?.*[A-Z]', next_line):
                        break
                    if re.match(r'(Module|PART)\s', next_line, re.IGNORECASE):
                        break
                    if not next_line:
                        j += 1
                        continue
                    
                    q_text += ' ' + next_line
                    j += 1
                
                # Clean text
                q_text = re.sub(r'\s+', ' ', q_text).strip()
                
                # Extract marks - handle multiple formats
                marks = None
                # Try "X marks" format
                marks_match = re.search(r'\(?\s*(\d{1,2})\s*marks?\)?\s*$', q_text, re.IGNORECASE)
                if marks_match:
                    try:
                        m = int(marks_match.group(1))
                        if m <= 14:
                            marks = m
                            q_text = q_text[:marks_match.start()].strip()
                    except ValueError:
                        pass
                
                # Try plain number at end if no marks found
                if marks is None:
                    num_match = re.search(r'\s+(\d{1,2})\s*$', q_text)
                    if num_match:
                        try:
                            m = int(num_match.group(1))
                            if m <= 14:
                                marks = m
                                q_text = q_text[:num_match.start()].strip()
                        except ValueError:
                            pass
                
                q_full_num = f"{q_num}{sub.lower()}" if sub else q_num
                
                # Determine part based on question number
                try:
                    is_part_a = int(q_num) <= 10
                except ValueError:
                    is_part_a = False
                
                if marks is None:
                    marks = 3 if is_part_a else 7
                
                # Accept question if reasonably long and starts with letter
                if len(q_text) >= 10 and re.match(r'^[A-Za-z]', q_text):
                    questions.append({
                        'question_number': q_full_num,
                        'text': q_text,
                        'marks': marks,
                        'part': 'A' if is_part_a else 'B',
                        'module_hint': current_module if not is_part_a else None,
                    })
                
                i = j
                continue
            
            i += 1
        
        return questions
    
    def _deduplicate(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate questions while preserving order."""
        seen = set()
        unique = []
        
        for q in questions:
            # Create key from number and first part of text
            key = (q['question_number'], q['text'][:30].lower().strip())
            if key not in seen and len(q['text']) >= 10:
                seen.add(key)
                unique.append(q)
        
        return unique
    
    def get_page_count(self, pdf_path: str) -> int:
        """Get the number of pages in a PDF."""
        if self.pdfplumber:
            try:
                with self.pdfplumber.open(pdf_path) as pdf:
                    return len(pdf.pages)
            except Exception:
                pass
        
        if self.fitz:
            try:
                doc = self.fitz.open(pdf_path)
                count = len(doc)
                doc.close()
                return count
            except Exception:
                pass
        
        return 0
