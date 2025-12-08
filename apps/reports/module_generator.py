"""
Module-wise PDF report generator.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import defaultdict
from django.template.loader import render_to_string
from django.conf import settings

from apps.subjects.models import Subject, Module
from apps.questions.models import Question
from apps.analytics.models import TopicCluster

logger = logging.getLogger(__name__)


class ModuleReportGenerator:
    """Generates individual PDF reports for each module."""
    
    def __init__(self, subject: Subject):
        self.subject = subject
    
    def generate_all_modules(self) -> List[str]:
        """
        Generate PDF reports for all modules.
        
        Returns:
            List of paths to generated PDF files
        """
        modules = self.subject.modules.all().order_by('number')
        pdf_paths = []
        
        for module in modules:
            pdf_path = self.generate_module_report(module)
            if pdf_path:
                pdf_paths.append(pdf_path)
        
        logger.info(f"Generated {len(pdf_paths)} module reports for {self.subject.name}")
        return pdf_paths
    
    def generate_module_report(self, module: Module) -> Optional[str]:
        """
        Generate PDF report for a single module.
        
        Args:
            module: Module instance
            
        Returns:
            Path to generated PDF file, or None on failure
        """
        try:
            from weasyprint import HTML
            
            # Gather questions for this module
            questions = Question.objects.filter(
                paper__subject=self.subject,
                module=module
            ).select_related('paper').order_by('paper__year', 'question_number')
            
            if not questions.exists():
                logger.warning(f"No questions found for module {module.number}")
                return None
            
            # Organize questions by part and year
            part_a_questions = []
            part_b_questions = []
            part_a_by_year = defaultdict(list)
            part_b_by_year = defaultdict(list)
            
            for question in questions:
                # Determine part from question number
                try:
                    q_num = int(''.join(filter(str.isdigit, question.question_number)))
                    is_part_a = q_num <= 10
                except (ValueError, TypeError):
                    # Default to Part B if can't determine
                    is_part_a = False
                
                year = question.paper.year if question.paper else 'Unknown'
                
                if is_part_a:
                    part_a_questions.append(question)
                    part_a_by_year[year].append(question)
                else:
                    part_b_questions.append(question)
                    part_b_by_year[year].append(question)
            
            # Get topic clusters for this module
            topic_clusters = TopicCluster.objects.filter(
                subject=self.subject,
                module=module
            ).order_by('priority_tier', '-frequency_count')
            
            # Organize topics by tier
            tier_1_topics = []
            tier_2_topics = []
            tier_3_topics = []
            tier_4_topics = []
            
            for cluster in topic_clusters:
                topic_data = {
                    'topic_name': cluster.topic_name,
                    'frequency_count': cluster.frequency_count,
                    'years_appeared': cluster.years_appeared,
                    'total_marks': cluster.total_marks,
                    'avg_marks': round(cluster.avg_marks, 1),
                }
                
                if cluster.priority_tier == 1:
                    tier_1_topics.append(topic_data)
                elif cluster.priority_tier == 2:
                    tier_2_topics.append(topic_data)
                elif cluster.priority_tier == 3:
                    tier_3_topics.append(topic_data)
                else:
                    tier_4_topics.append(topic_data)
            
            # Get exam pattern for marks
            exam_pattern = self.subject.get_exam_pattern()
            part_a_marks = exam_pattern.get('part_a', {}).get('marks_per_question', 3)
            part_b_marks = exam_pattern.get('part_b', {}).get('marks_per_question', 14)
            
            # Prepare context
            context = {
                'subject': self.subject,
                'module': module,
                'total_modules': self.subject.modules.count(),
                'part_a_questions': part_a_questions,
                'part_b_questions': part_b_questions,
                'part_a_by_year': dict(part_a_by_year),
                'part_b_by_year': dict(part_b_by_year),
                'part_a_marks': part_a_marks,
                'part_b_marks': part_b_marks,
                'topic_clusters': topic_clusters,
                'tier_1_topics': tier_1_topics,
                'tier_2_topics': tier_2_topics,
                'tier_3_topics': tier_3_topics,
                'tier_4_topics': tier_4_topics,
                'all_topics_sorted': tier_1_topics + tier_2_topics + tier_3_topics + tier_4_topics,
                'papers_count': self.subject.papers.count(),
            }
            
            # Render HTML
            html_content = render_to_string('reports/module_wise_report.html', context)
            
            # Generate PDF
            output_dir = Path(settings.MEDIA_ROOT) / 'reports' / str(self.subject.id)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"Module_{module.number}_{self.subject.code.replace(' ', '_')}.pdf"
            output_path = output_dir / filename
            
            HTML(string=html_content).write_pdf(str(output_path))
            
            logger.info(f"Generated module report: {output_path}")
            return str(output_path)
            
        except ImportError:
            logger.error("WeasyPrint not installed")
            return None
        except Exception as e:
            logger.error(f"Module report generation failed: {e}", exc_info=True)
            return None
    
    def get_report_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about available reports.
        
        Returns:
            Dict with report information
        """
        modules = self.subject.modules.all().order_by('number')
        reports = []
        
        output_dir = Path(settings.MEDIA_ROOT) / 'reports' / str(self.subject.id)
        
        for module in modules:
            filename = f"Module_{module.number}_{self.subject.code.replace(' ', '_')}.pdf"
            file_path = output_dir / filename
            
            reports.append({
                'module_number': module.number,
                'module_name': module.name,
                'filename': filename,
                'exists': file_path.exists(),
                'path': str(file_path) if file_path.exists() else None,
                'url': f"/media/reports/{self.subject.id}/{filename}" if file_path.exists() else None,
            })
        
        return {
            'subject': self.subject,
            'reports': reports,
            'total_modules': len(reports),
            'generated_count': sum(1 for r in reports if r['exists']),
        }
