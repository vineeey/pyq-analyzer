"""Views for report generation and download."""
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.contrib import messages
from pathlib import Path
import logging

from apps.subjects.models import Subject, Module
from .generator import ReportGenerator
from .module_report_generator import ModuleReportGenerator

logger = logging.getLogger(__name__)


class ReportsListView(LoginRequiredMixin, TemplateView):
    """List available reports for a subject."""
    
    template_name = 'reports/reports_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = get_object_or_404(
            Subject, pk=self.kwargs['subject_pk'], user=self.request.user
        )
        
        context['subject'] = subject
        context['modules'] = subject.modules.all().order_by('number')
        
        return context


class GenerateModuleReportView(LoginRequiredMixin, View):
    """Generate and download a specific module report."""
    
    def get(self, request, subject_pk, module_number):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        module = get_object_or_404(Module, subject=subject, number=module_number)
        
        try:
            generator = ModuleReportGenerator(subject)
            pdf_path = generator.generate_module_report(module)
            
            if pdf_path and Path(pdf_path).exists():
                filename = f"Module_{module.number}_{subject.code or 'subject'}.pdf"
                return FileResponse(
                    open(pdf_path, 'rb'),
                    content_type='application/pdf',
                    as_attachment=True,
                    filename=filename
                )
            
            messages.error(request, f"Failed to generate report for Module {module.number}")
            raise Http404("Report generation failed")
        except Exception as e:
            logger.exception(f"Report generation error for module {module_number}: {e}")
            messages.error(request, f"Error generating report: {str(e)}")
            raise Http404("Report generation failed")


class GenerateAllModuleReportsView(LoginRequiredMixin, View):
    """Generate reports for all modules."""
    
    def get(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        try:
            generator = ModuleReportGenerator(subject)
            results = generator.generate_all_module_reports()
            
            # Return the first successfully generated report
            # In a real implementation, we'd zip all PDFs together
            for module_num, pdf_path in results.items():
                if pdf_path and Path(pdf_path).exists():
                    return FileResponse(
                        open(pdf_path, 'rb'),
                        content_type='application/pdf',
                        as_attachment=True,
                        filename=f"Module_{module_num}_{subject.code or 'subject'}.pdf"
                    )
            
            messages.error(request, "No reports could be generated")
            raise Http404("Report generation failed")
        except Exception as e:
            logger.exception(f"Report generation error for subject {subject_pk}: {e}")
            messages.error(request, f"Error generating reports: {str(e)}")
            raise Http404("Report generation failed")


class GenerateAnalyticsReportView(LoginRequiredMixin, View):
    """Generate and download analytics summary report."""
    
    def get(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        generator = ReportGenerator(subject)
        pdf_path = generator.generate_analytics_report()
        
        if pdf_path and Path(pdf_path).exists():
            return FileResponse(
                open(pdf_path, 'rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=f'{subject.code or subject.name}_analytics_report.pdf'
            )
        
        messages.error(request, "Failed to generate analytics report")
        raise Http404("Report generation failed")
