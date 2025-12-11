/**
 * PYQ Analyzer - Main JavaScript
 * Enhanced with modern animations and interactions
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Re-initialize icons after HTMX swaps
    document.body.addEventListener('htmx:afterSwap', function() {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    });
    
    // Initialize GSAP animations if available
    initGSAPAnimations();
    
    // Initialize smooth scrolling
    initSmoothScroll();
    
    // Initialize parallax effects
    initParallax();
});

// HTMX configuration
document.body.addEventListener('htmx:configRequest', function(evt) {
    // Add CSRF token to all HTMX requests
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        evt.detail.headers['X-CSRFToken'] = csrfToken.value;
    }
});

// File upload preview
function previewFile(input, previewId) {
    const preview = document.getElementById(previewId);
    if (input.files && input.files[0]) {
        const file = input.files[0];
        preview.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Chart.js default configuration with error handling
if (typeof Chart !== 'undefined') {
    try {
        if (Chart.defaults) {
            if (Chart.defaults.font) {
                Chart.defaults.font.family = 'Inter, system-ui, -apple-system, sans-serif';
            }
            if (Chart.defaults.plugins && Chart.defaults.plugins.legend) {
                Chart.defaults.plugins.legend.position = 'bottom';
            }
            Chart.defaults.color = '#6B7280';
            Chart.defaults.borderColor = 'rgba(99, 102, 241, 0.1)';
        }
    } catch (error) {
        console.warn('Chart.js configuration failed:', error);
    }
}

// Initialize GSAP animations
function initGSAPAnimations() {
    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;
    
    gsap.registerPlugin(ScrollTrigger);
    
    // Fade in elements on scroll
    const fadeElements = document.querySelectorAll('.scroll-fade-in');
    fadeElements.forEach((el) => {
        gsap.from(el, {
            scrollTrigger: {
                trigger: el,
                start: 'top 85%',
                toggleActions: 'play none none reverse'
            },
            opacity: 0,
            y: 30,
            duration: 0.8,
            ease: 'power2.out'
        });
    });
    
    // Stagger animation for lists
    const staggerElements = document.querySelectorAll('.stagger-fade-in');
    if (staggerElements.length > 0) {
        gsap.from(staggerElements, {
            scrollTrigger: {
                trigger: staggerElements[0],
                start: 'top 85%',
                toggleActions: 'play none none reverse'
            },
            opacity: 0,
            y: 20,
            duration: 0.6,
            stagger: 0.1,
            ease: 'power2.out'
        });
    }
}

// Smooth scrolling for anchor links
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Parallax scrolling effect
function initParallax() {
    const parallaxElements = document.querySelectorAll('.parallax');
    if (parallaxElements.length === 0) return;
    
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        parallaxElements.forEach(el => {
            const speed = el.dataset.speed || 0.5;
            el.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });
}

// Loading animation helper
function showLoader(elementId) {
    const loader = document.getElementById(elementId);
    if (loader) {
        loader.classList.remove('hidden');
        loader.classList.add('flex');
    }
}

function hideLoader(elementId) {
    const loader = document.getElementById(elementId);
    if (loader) {
        loader.classList.remove('flex');
        loader.classList.add('hidden');
    }
}

// Toast notification system
function showToast(message, type = 'info', duration = 3000) {
    const colors = {
        success: 'from-green-500 to-green-600',
        error: 'from-red-500 to-red-600',
        warning: 'from-yellow-500 to-yellow-600',
        info: 'from-blue-500 to-blue-600'
    };
    
    const toast = document.createElement('div');
    toast.className = `fixed top-20 right-4 z-50 px-6 py-4 rounded-2xl shadow-2xl bg-gradient-to-r ${colors[type]} text-white backdrop-blur-sm transform translate-x-full transition-transform duration-300`;
    toast.innerHTML = `
        <div class="flex items-center space-x-3">
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-white/80 hover:text-white transition-colors">
                <i data-lucide="x" class="w-5 h-5"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(toast);
    lucide.createIcons();
    
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 10);
    
    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Clipboard copy functionality
function copyToClipboard(text, buttonElement) {
    navigator.clipboard.writeText(text).then(() => {
        if (buttonElement) {
            const originalText = buttonElement.innerHTML;
            buttonElement.innerHTML = '<i data-lucide="check" class="w-4 h-4"></i>';
            lucide.createIcons();
            setTimeout(() => {
                buttonElement.innerHTML = originalText;
                lucide.createIcons();
            }, 2000);
        }
        showToast('Copied to clipboard!', 'success', 2000);
    }).catch(() => {
        showToast('Failed to copy', 'error', 2000);
    });
}

// Enhanced form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('border-red-500');
            input.classList.remove('border-gray-300');
        } else {
            input.classList.remove('border-red-500');
            input.classList.add('border-gray-300');
        }
    });
    
    return isValid;
}

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export for use in other scripts
window.PYQAnalyzer = {
    showToast,
    copyToClipboard,
    validateForm,
    showLoader,
    hideLoader,
    debounce
};
