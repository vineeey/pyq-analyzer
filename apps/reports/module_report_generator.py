"""
Enhanced module-wise PDF report generator matching the expected format.
Generates separate PDFs for each module with:
- Part A questions grouped by year
- Part B questions grouped by year
- Repeated Question Analysis with priority tiers
- Final Study Priority Order
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import defaultdict
from django.template.loader import render_to_string
from django.conf import settings

from apps.subjects.models import Subject, Module
from apps.questions.models import Question
from apps.analytics.models import TopicCluster

logger = logging.getLogger(__name__)


class ModuleReportGenerator:
    """Generates detailed module-wise PDF reports."""
    
    def __init__(self, subject: Subject):
        self.subject = subject
    
    def generate_all_module_reports(self) -> Dict[int, Optional[str]]:
        """
        Generate PDF reports for all modules in the subject.
        
        Returns:
            Dictionary mapping module number to PDF file path
        """
        results = {}
        modules = self.subject.modules.all().order_by('number')
        
        for module in modules:
            pdf_path = self.generate_module_report(module)
            results[module.number] = pdf_path
        
        return results
    
    def generate_module_report(self, module: Module) -> Optional[str]:
        """
        Generate a PDF report for a single module.
        
        Args:
            module: Module instance
            
        Returns:
            Path to generated PDF file, or None on failure
        """
        try:
            from weasyprint import HTML, CSS
            
            # Gather all data for this module
            report_data = self._prepare_module_data(module)
            
            # Render HTML template
            html_content = render_to_string('reports/module_report_detailed.html', report_data)
            
            # Generate PDF
            output_dir = Path(settings.MEDIA_ROOT) / 'reports' / str(self.subject.id)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"Module_{module.number}_{self.subject.code or 'subject'}.pdf"
            output_path = output_dir / filename
            
            # Custom CSS for better formatting
            css_str = """
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: 'DejaVu Sans', Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
            }
            h1 {
                color: #2c3e50;
                font-size: 24pt;
                margin-bottom: 10px;
            }
            h2 {
                color: #34495e;
                font-size: 18pt;
                margin-top: 20px;
                border-bottom: 2px solid #3498db;
                padding-bottom: 5px;
            }
            h3 {
                color: #7f8c8d;
                font-size: 14pt;
                margin-top: 15px;
            }
            .priority-tier-1 {
                background-color: #e74c3c;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            .priority-tier-2 {
                background-color: #e67e22;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            .priority-tier-3 {
                background-color: #f39c12;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            .priority-tier-4 {
                background-color: #95a5a6;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
            }
            .question-block {
                margin-left: 20px;
                margin-bottom: 10px;
            }
            .year-label {
                font-weight: bold;
                color: #3498db;
            }
            .marks {
                color: #27ae60;
                font-style: italic;
            }
            ul {
                margin-left: 20px;
            }
            """
            
            HTML(string=html_content).write_pdf(
                str(output_path),
                stylesheets=[CSS(string=css_str)]
            )
            
            logger.info(f"Generated module report: {output_path}")
            return str(output_path)
            
        except ImportError:
            logger.error("WeasyPrint not installed")
            return None
        except Exception as e:
            logger.error(f"Module report generation failed: {e}", exc_info=True)
            return None
    
    def _prepare_module_data(self, module: Module) -> Dict[str, Any]:
        """
        Prepare all data needed for the module report.
        """
        # Get all questions for this module
        questions = Question.objects.filter(
            module=module
        ).select_related('paper', 'topic_cluster').order_by('paper__year', 'question_number')
        
        # Group questions by part and year
        part_a_by_year = self._group_questions_by_year(questions.filter(part='A'))
        part_b_by_year = self._group_questions_by_year(questions.filter(part='B'))
        
        # Get topic clusters with priority tiers
        topic_clusters = TopicCluster.objects.filter(
            module=module
        ).order_by('-frequency_count', 'topic_name')
        
        # Group topics by priority tier
        topics_by_tier = self._group_topics_by_tier(topic_clusters)
        
        # Create study priority order (sorted list)
        study_priority = self._create_study_priority_order(topic_clusters)
        
        return {
            'subject': self.subject,
            'module': module,
            'part_a_by_year': part_a_by_year,
            'part_b_by_year': part_b_by_year,
            'topics_by_tier': topics_by_tier,
            'study_priority': study_priority,
            'total_questions': questions.count(),
            'total_part_a': questions.filter(part='A').count(),
            'total_part_b': questions.filter(part='B').count(),
        }
    
    def _group_questions_by_year(self, questions) -> Dict[str, List[Question]]:
        """Group questions by exam year."""
        grouped = defaultdict(list)
        for q in questions:
            year_label = q.paper.year or 'Unknown'
            grouped[year_label].append(q)
        return dict(sorted(grouped.items()))
    
    def _group_topics_by_tier(self, topic_clusters) -> Dict[str, List[TopicCluster]]:
        """Group topic clusters by priority tier."""
        grouped = defaultdict(list)
        for cluster in topic_clusters:
            tier_label = cluster.get_tier_label()
            grouped[tier_label].append(cluster)
        
        # Return in order: Top -> High -> Medium -> Low
        tier_order = ['Top Priority', 'High Priority', 'Medium Priority', 'Low Priority']
        result = {}
        for tier in tier_order:
            if tier in grouped:
                result[tier] = grouped[tier]
        return result
    
    def _create_study_priority_order(self, topic_clusters) -> List[Dict[str, Any]]:
        """
        Create ordered list of topics for studying.
        Returns list of dicts with topic info and recommendations.
        """
        priority_order = []
        
        for rank, cluster in enumerate(topic_clusters, 1):
            # Create study recommendation
            freq = cluster.frequency_count
            years = ', '.join(cluster.years_appeared) if cluster.years_appeared else 'N/A'
            
            if freq >= 4:
                recommendation = f"**MUST STUDY** - Appeared {freq} times. Extremely high probability."
            elif freq == 3:
                recommendation = f"High importance - Appeared {freq} times. Strong preparation recommended."
            elif freq == 2:
                recommendation = f"Moderate importance - Appeared {freq} times. Good to prepare."
            else:
                recommendation = f"Low priority - Appeared {freq} time. Study if time permits."
            
            priority_order.append({
                'rank': rank,
                'topic': cluster.topic_name,
                'frequency': freq,
                'years': years,
                'total_marks': cluster.total_marks,
                'tier': cluster.get_tier_label(),
                'recommendation': recommendation,
                'representative_text': cluster.representative_text[:200] if cluster.representative_text else '',
            })
        
        return priority_order


def generate_module_reports(subject: Subject) -> Dict[int, Optional[str]]:
    """
    Convenience function to generate all module reports for a subject.
    
    Args:
        subject: Subject instance
        
    Returns:
        Dictionary mapping module number to PDF file path
    """
    generator = ModuleReportGenerator(subject)
    return generator.generate_all_module_reports()
