"""Views for paper upload and management."""
from django.views.generic import ListView, DetailView, CreateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
import hashlib

from apps.subjects.models import Subject
from .models import Paper
from .forms import PaperUploadForm, BatchPaperUploadForm


class PaperListView(LoginRequiredMixin, ListView):
    """List papers for a subject."""
    
    model = Paper
    template_name = 'papers/paper_list.html'
    context_object_name = 'papers'
    
    def get_queryset(self):
        self.subject = get_object_or_404(
            Subject, pk=self.kwargs['subject_pk'], user=self.request.user
        )
        return Paper.objects.filter(subject=self.subject).order_by('-year', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = self.subject
        return context


class PaperDetailView(LoginRequiredMixin, DetailView):
    """View paper details and extracted questions."""
    
    model = Paper
    template_name = 'papers/paper_detail.html'
    context_object_name = 'paper'
    
    def get_queryset(self):
        return Paper.objects.filter(subject__user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = self.object.questions.all().select_related('module')
        return context


class PaperUploadView(LoginRequiredMixin, FormView):
    """Upload multiple question papers at once."""
    
    form_class = BatchPaperUploadForm
    template_name = 'papers/paper_upload.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.subject = get_object_or_404(
            Subject, pk=kwargs['subject_pk'], user=request.user
        )
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = self.subject
        return context
    
    def get_success_url(self):
        return reverse_lazy('papers:list', kwargs={'subject_pk': self.subject.pk})
    
    def post(self, request, *args, **kwargs):
        """Handle file upload - bypass form validation and handle files directly."""
        files = request.FILES.getlist('files')
        university = request.POST.get('university', 'ktu')
        
        if not files:
            messages.error(request, 'Please select at least one PDF file.')
            return self.get(request, *args, **kwargs)
        
        # Validate files
        for f in files:
            if not f.name.lower().endswith('.pdf'):
                messages.error(request, f'"{f.name}" is not a PDF file. Only PDF files are supported.')
                return self.get(request, *args, **kwargs)
            if f.size > 50 * 1024 * 1024:
                messages.error(request, f'"{f.name}" exceeds 50MB limit.')
                return self.get(request, *args, **kwargs)
        
        # Process files
        uploaded_count = 0
        for uploaded_file in files:
            # Parse filename for metadata
            parsed = BatchPaperUploadForm.parse_filename(uploaded_file.name)
            
            # Calculate file hash for deduplication
            file_hash = hashlib.sha256()
            for chunk in uploaded_file.chunks():
                file_hash.update(chunk)
            file_hash_hex = file_hash.hexdigest()
            uploaded_file.seek(0)  # Reset file pointer
            
            # Check if file already exists (by hash)
            if Paper.objects.filter(subject=self.subject, file_hash=file_hash_hex).exists():
                messages.warning(
                    request,
                    f'"{uploaded_file.name}" already uploaded (skipped)'
                )
                continue
            
            # Create paper
            paper = Paper.objects.create(
                subject=self.subject,
                title=parsed['title'],
                year=parsed['year'],
                exam_type=parsed['exam_type'],
                file=uploaded_file,
                file_hash=file_hash_hex,
                university=university,
            )
            uploaded_count += 1
            
            # Queue background analysis task
            try:
                from apps.analysis.tasks import queue_paper_analysis
                queue_paper_analysis(paper)
            except Exception as e:
                messages.warning(
                    request,
                    f'"{uploaded_file.name}" uploaded but analysis could not be queued: {str(e)}'
                )
        
        if uploaded_count > 0:
            messages.success(
                request,
                f'{uploaded_count} paper(s) uploaded successfully! Analysis has been queued.'
            )
        
        return redirect(self.get_success_url())


class PaperDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a paper."""
    
    model = Paper
    template_name = 'papers/paper_confirm_delete.html'
    
    def get_queryset(self):
        return Paper.objects.filter(subject__user=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy('papers:list', kwargs={'subject_pk': self.object.subject.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Paper "{self.object.title}" deleted.')
        return super().form_valid(form)
