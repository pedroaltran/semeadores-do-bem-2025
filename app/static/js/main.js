/**
 * Semeadores do Bem - JavaScript Principal
 * Este arquivo contém toda a funcionalidade JavaScript da landing page
 * 
 * Funcionalidades:
 * - Menu mobile responsivo
 * - Scroll suave para âncoras
 * - Navbar com efeito ao fazer scroll
 * - Formulário de contato/colaborador
 * - Animações ao aparecer na tela (scroll animations)
 * - Botão de voltar ao topo
 */

// ===== Configurações Globais =====
const CONFIG = {
    scrollOffset: 80, // Altura da navbar fixa
    animationDelay: 100,
    scrollThreshold: 100
};

// ===== Inicialização =====
document.addEventListener('DOMContentLoaded', function() {
    initMobileMenu();
    initSmoothScroll();
    initNavbarScroll();
    initFormHandlers();
    initScrollAnimations();
    initScrollToTop();
    initDropdownMenus();
});

// ===== Menu Mobile =====
function initMobileMenu() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (!mobileMenuButton || !mobileMenu) return;
    
    mobileMenuButton.addEventListener('click', function() {
        mobileMenu.classList.toggle('hidden');
        
        // Anima o ícone do menu
        const icon = mobileMenuButton.querySelector('i');
        if (icon) {
            icon.classList.toggle('fa-bars');
            icon.classList.toggle('fa-times');
        }
    });
    
    // Fecha o menu ao clicar em um link
    const mobileLinks = mobileMenu.querySelectorAll('a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', function() {
            mobileMenu.classList.add('hidden');
            const icon = mobileMenuButton.querySelector('i');
            if (icon) {
                icon.classList.add('fa-bars');
                icon.classList.remove('fa-times');
            }
        });
    });
}

// ===== Scroll Suave =====
function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (!targetElement) return;
            
            const targetPosition = targetElement.offsetTop - CONFIG.scrollOffset;
            
            window.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
        });
    });
}

// ===== Navbar ao Fazer Scroll =====
function initNavbarScroll() {
    const navbar = document.querySelector('nav');
    if (!navbar) return;
    
    let lastScroll = 0;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        // Adiciona sombra quando faz scroll
        if (currentScroll > CONFIG.scrollThreshold) {
            navbar.classList.add('shadow-lg');
        } else {
            navbar.classList.remove('shadow-lg');
        }
        
        // Esconde/mostra navbar baseado na direção do scroll (opcional)
        // if (currentScroll > lastScroll && currentScroll > 500) {
        //     navbar.style.transform = 'translateY(-100%)';
        // } else {
        //     navbar.style.transform = 'translateY(0)';
        // }
        
        lastScroll = currentScroll;
    });
}

// ===== Manipulador de Formulários =====
function initFormHandlers() {
    const colaboradorForm = document.getElementById('colaborador-form');
    
    if (colaboradorForm) {
        colaboradorForm.addEventListener('submit', handleColaboradorForm);
    }
}

async function handleColaboradorForm(e) {
    e.preventDefault();
    
    const form = e.target;
    const feedback = document.getElementById('colaborador-feedback');
    const submitButton = form.querySelector('button[type="submit"]');
    
    // Mostra loading
    const originalButtonText = submitButton.innerHTML;
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Enviando...';
    
    try {
        const formData = new FormData(form);
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // Sucesso
            showFeedback(feedback, 'success', 'Mensagem enviada com sucesso! Entraremos em contato em breve.');
            form.reset();
        } else {
            // Erro
            showFeedback(feedback, 'error', 'Erro ao enviar mensagem. Por favor, tente novamente.');
        }
    } catch (error) {
        console.error('Erro:', error);
        showFeedback(feedback, 'error', 'Erro de conexão. Por favor, verifique sua internet e tente novamente.');
    } finally {
        // Restaura o botão
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    }
}

function showFeedback(element, type, message) {
    if (!element) return;
    
    const classes = type === 'success' 
        ? 'bg-green-100 text-green-700 border-green-400' 
        : 'bg-red-100 text-red-700 border-red-400';
    
    element.innerHTML = `
        <div class="p-4 rounded-lg border ${classes} animate-fadeIn">
            <p class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} mr-2"></i>
                ${message}
            </p>
        </div>
    `;
    
    // Remove a mensagem após 5 segundos
    setTimeout(() => {
        element.innerHTML = '';
    }, 5000);
}

// ===== Animações ao Aparecer na Tela =====
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fadeIn');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Elementos para animar
    const animatedElements = document.querySelectorAll('.card, .box, section > div > *');
    animatedElements.forEach(el => observer.observe(el));
}

// ===== Botão Voltar ao Topo =====
function initScrollToTop() {
    // Cria o botão
    const scrollButton = document.createElement('button');
    scrollButton.innerHTML = '<i class="fas fa-arrow-up"></i>';
    scrollButton.className = 'scroll-to-top fixed bottom-4 left-4';
    document.body.appendChild(scrollButton);
    
    // Mostra/esconde baseado no scroll
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollButton.classList.add('visible');
        } else {
            scrollButton.classList.remove('visible');
        }
    });
    
    // Clique para voltar ao topo
    scrollButton.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// ===== Dropdown Menus =====
function initDropdownMenus() {
    const dropdowns = document.querySelectorAll('.group');
    
    dropdowns.forEach(dropdown => {
        const button = dropdown.querySelector('button');
        const menu = dropdown.querySelector('div');
        
        if (!button || !menu) return;
        
        // Adiciona ARIA attributes
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-haspopup', 'true');
        
        // Keyboard navigation
        button.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleDropdown(button, menu);
            }
        });
    });
}

function toggleDropdown(button, menu) {
    const isOpen = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', !isOpen);
}

// ===== Utilidades =====
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

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ===== Validação de Formulário =====
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            showFieldError(field, 'Este campo é obrigatório');
        } else {
            clearFieldError(field);
        }
        
        // Validação específica por tipo
        if (field.type === 'email' && field.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value)) {
                isValid = false;
                showFieldError(field, 'Por favor, insira um e-mail válido');
            }
        }
        
        if (field.type === 'tel' && field.value) {
            const phoneRegex = /^\(?[1-9]{2}\)? ?(?:[2-8]|9[1-9])[0-9]{3}\-?[0-9]{4}$/;
            if (!phoneRegex.test(field.value.replace(/\s/g, ''))) {
                isValid = false;
                showFieldError(field, 'Por favor, insira um telefone válido');
            }
        }
    });
    
    return isValid;
}

function showFieldError(field, message) {
    const errorElement = field.parentElement.querySelector('.field-error');
    if (errorElement) {
        errorElement.textContent = message;
    } else {
        const error = document.createElement('span');
        error.className = 'field-error text-red-500 text-sm mt-1';
        error.textContent = message;
        field.parentElement.appendChild(error);
    }
    field.classList.add('border-red-500');
}

function clearFieldError(field) {
    const errorElement = field.parentElement.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
    field.classList.remove('border-red-500');
}