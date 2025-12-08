"""Views for report generation and download."""
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse, Http404, JsonResponse
from django.contrib import messages
from pathlib import Path

from apps.subjects.models import Subject, Module
from .generator import ReportGenerator
from .module_generator import ModuleReportGenerator


class GenerateModuleReportView(LoginRequiredMixin, View):
    """Generate and download module report."""
    
    def get(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        generator = ReportGenerator(subject)
        pdf_path = generator.generate_module_report()
        
        if pdf_path and Path(pdf_path).exists():
            return FileResponse(
                open(pdf_path, 'rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=f'{subject.name}_module_report.pdf'
            )
        
        raise Http404("Report generation failed")


class GenerateAnalyticsReportView(LoginRequiredMixin, View):
    """Generate and download analytics report."""
    
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
                filename=f'{subject.name}_analytics_report.pdf'
            )
        
        raise Http404("Report generation failed")


class ModuleReportsView(LoginRequiredMixin, TemplateView):
    """View to manage and download module-wise reports."""
    
    template_name = 'reports/module_reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = get_object_or_404(
            Subject, pk=self.kwargs['subject_pk'], user=self.request.user
        )
        
        generator = ModuleReportGenerator(subject)
        metadata = generator.get_report_metadata()
        
        context['subject'] = subject
        context['reports'] = metadata['reports']
        context['total_modules'] = metadata['total_modules']
        context['generated_count'] = metadata['generated_count']
        
        return context


class GenerateAllModuleReportsView(LoginRequiredMixin, View):
    """Generate all module reports."""
    
    def post(self, request, subject_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        
        generator = ModuleReportGenerator(subject)
        pdf_paths = generator.generate_all_modules()
        
        if pdf_paths:
            messages.success(
                request,
                f'Successfully generated {len(pdf_paths)} module reports!'
            )
        else:
            messages.error(request, 'Failed to generate module reports.')
        
        return redirect('reports:module_reports', subject_pk=subject_pk)


class GenerateSingleModuleReportView(LoginRequiredMixin, View):
    """Generate report for a single module."""
    
    def get(self, request, subject_pk, module_pk):
        subject = get_object_or_404(
            Subject, pk=subject_pk, user=request.user
        )
        module = get_object_or_404(
            Module, pk=module_pk, subject=subject
        )
        
        generator = ModuleReportGenerator(subject)
        pdf_path = generator.generate_module_report(module)
        
        if pdf_path and Path(pdf_path).exists():
            return FileResponse(
                open(pdf_path, 'rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=f'Module_{module.number}_{subject.code}.pdf'
            )
        
        raise Http404("Module report generation failed")
