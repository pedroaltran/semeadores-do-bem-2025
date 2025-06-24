/**
 * Semeadores do Bem - Blog JavaScript
 * Este arquivo contém as funcionalidades específicas para as páginas do blog
 * 
 * Funcionalidades:
 * - Verificação de autenticação do usuário
 * - Menu mobile responsivo
 * - Busca de posts
 * - Compartilhamento social
 * - Lazy loading de imagens
 * - Animações de scroll
 */

// ===== Configurações =====
const API_ENDPOINTS = {
    checkUser: '/me',
    logout: '/logout',
    search: '/blog/search'
};

// ===== Inicialização =====
document.addEventListener('DOMContentLoaded', function() {
    initializeAuth();
    initializeMobileMenu();
    initializeSearch();
    initializeLazyLoading();
    initializeShareButtons();
    initializeReadingProgress();
    initializeScrollAnimations();
});

// ===== Autenticação =====
async function initializeAuth() {
    try {
        const response = await fetch(API_ENDPOINTS.checkUser);
        const data = await response.json();
        
        updateNavigationMenu(response.ok && data.email, data.email);
    } catch (error) {
        console.error('Erro ao verificar autenticação:', error);
        updateNavigationMenu(false, null);
    }
}

function updateNavigationMenu(isAuthenticated, userEmail) {
    const desktopNavMenu = document.getElementById('nav-menu');
    const mobileNavMenu = document.getElementById('mobile-nav-menu');
    
    if (isAuthenticated && userEmail) {
        const authMenuHTML = `
            <div class="flex items-center space-x-4">
                <div class="flex items-center text-gray-700">
                    <i class="fas fa-user-circle text-2xl text-primary mr-2"></i>
                    <span class="text-sm font-medium">${userEmail}</span>
                </div>
                <a href="/admin" class="bg-accent text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors">
                    <i class="fas fa-tachometer-alt mr-2"></i>
                    Admin
                </a>
                <a href="${API_ENDPOINTS.logout}" class="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors">
                    <i class="fas fa-sign-out-alt mr-2"></i>
                    Sair
                </a>
            </div>
        `;
        
        const mobileAuthMenuHTML = `
            <div class="space-y-2">
                <div class="flex items-center text-gray-700 px-3 py-2">
                    <i class="fas fa-user-circle text-xl text-primary mr-2"></i>
                    <span class="text-sm">${userEmail}</span>
                </div>
                <a href="/admin" class="block px-3 py-2 bg-accent text-white rounded-lg">
                    <i class="fas fa-tachometer-alt mr-2"></i>
                    Painel Admin
                </a>
                <a href="${API_ENDPOINTS.logout}" class="block px-3 py-2 bg-gray-200 text-gray-700 rounded-lg">
                    <i class="fas fa-sign-out-alt mr-2"></i>
                    Sair
                </a>
            </div>
        `;
        
        if (desktopNavMenu) desktopNavMenu.innerHTML = authMenuHTML;
        if (mobileNavMenu) mobileNavMenu.innerHTML = mobileAuthMenuHTML;
    } else {
        const guestMenuHTML = `
            <div class="flex items-center space-x-3">
                <a href="/login" class="bg-primary text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors font-semibold">
                    <i class="fas fa-sign-in-alt mr-2"></i>
                    Entrar
                </a>
                <a href="/signup" class="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors font-semibold">
                    <i class="fas fa-user-plus mr-2"></i>
                    Cadastrar
                </a>
            </div>
        `;
        
        const mobileGuestMenuHTML = `
            <div class="space-y-2">
                <a href="/login" class="block px-3 py-2 bg-primary text-white rounded-lg text-center">
                    <i class="fas fa-sign-in-alt mr-2"></i>
                    Entrar
                </a>
                <a href="/signup" class="block px-3 py-2 bg-gray-200 text-gray-700 rounded-lg text-center">
                    <i class="fas fa-user-plus mr-2"></i>
                    Cadastrar
                </a>
            </div>
        `;
        
        if (desktopNavMenu) desktopNavMenu.innerHTML = guestMenuHTML;
        if (mobileNavMenu) mobileNavMenu.innerHTML = mobileGuestMenuHTML;
    }
}

// ===== Menu Mobile =====
function initializeMobileMenu() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (!mobileMenuButton || !mobileMenu) return;
    
    mobileMenuButton.addEventListener('click', function() {
        const isOpen = !mobileMenu.classList.contains('hidden');
        
        if (isOpen) {
            mobileMenu.classList.add('hidden');
            this.innerHTML = '<i class="fas fa-bars text-2xl"></i>';
        } else {
            mobileMenu.classList.remove('hidden');
            this.innerHTML = '<i class="fas fa-times text-2xl"></i>';
        }
    });
    
    // Fechar menu ao clicar em links
    const mobileLinks = mobileMenu.querySelectorAll('a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.classList.add('hidden');
            mobileMenuButton.innerHTML = '<i class="fas fa-bars text-2xl"></i>';
        });
    });
}

// ===== Busca de Posts =====
function initializeSearch() {
    // Adicionar formulário de busca se não existir
    const heroSection = document.querySelector('.pt-32');
    if (heroSection && !document.getElementById('search-form')) {
        const searchFormHTML = `
            <div class="mt-8 max-w-xl mx-auto">
                <form id="search-form" class="relative">
                    <input type="text" 
                           id="search-input"
                           placeholder="Buscar posts..." 
                           class="w-full px-6 py-3 pr-12 border-2 border-gray-200 rounded-full focus:outline-none focus:border-primary transition-colors">
                    <button type="submit" 
                            class="absolute right-2 top-1/2 transform -translate-y-1/2 bg-primary text-white px-4 py-2 rounded-full hover:bg-orange-600 transition-colors">
                        <i class="fas fa-search"></i>
                    </button>
                </form>
            </div>
        `;
        
        const container = heroSection.querySelector('.container');
        if (container) {
            container.insertAdjacentHTML('beforeend', searchFormHTML);
            
            const searchForm = document.getElementById('search-form');
            searchForm.addEventListener('submit', handleSearch);
        }
    }
}

function handleSearch(e) {
    e.preventDefault();
    const searchInput = document.getElementById('search-input');
    const query = searchInput.value.trim();
    
    if (query) {
        window.location.href = `/blog/search?q=${encodeURIComponent(query)}`;
    }
}

// ===== Lazy Loading de Imagens =====
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('fade-in');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback para navegadores sem suporte
        images.forEach(img => {
            img.src = img.dataset.src;
        });
    }
}

// ===== Botões de Compartilhamento =====
function initializeShareButtons() {
    const shareButtons = document.querySelectorAll('[data-share]');
    
    shareButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const network = this.dataset.share;
            const url = encodeURIComponent(window.location.href);
            const title = encodeURIComponent(document.title);
            
            let shareUrl = '';
            
            switch(network) {
                case 'facebook':
                    shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
                    break;
                case 'twitter':
                    shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${title}`;
                    break;
                case 'whatsapp':
                    shareUrl = `https://wa.me/?text=${title} - ${url}`;
                    break;
                case 'linkedin':
                    shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${url}`;
                    break;
            }
            
            if (shareUrl) {
                window.open(shareUrl, 'share', 'width=600,height=400');
            }
        });
    });
}

// ===== Indicador de Progresso de Leitura =====
function initializeReadingProgress() {
    // Só inicializar na página de post individual
    if (!document.querySelector('.prose')) return;
    
    const progressBar = document.createElement('div');
    progressBar.className = 'fixed top-0 left-0 h-1 bg-primary transition-all duration-300 z-50';
    progressBar.style.width = '0%';
    document.body.appendChild(progressBar);
    
    window.addEventListener('scroll', updateReadingProgress);
    
    function updateReadingProgress() {
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrolled = window.scrollY;
        const progress = (scrolled / docHeight) * 100;
        progressBar.style.width = `${progress}%`;
    }
}

// ===== Animações de Scroll =====
function initializeScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    
    if ('IntersectionObserver' in window) {
        const animationObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fadeIn');
                    animationObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px'
        });
        
        animatedElements.forEach(el => animationObserver.observe(el));
    }
}

// ===== Utilidades =====
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    return new Date(dateString).toLocaleDateString('pt-BR', options);
}

function estimateReadingTime(content) {
    const wordsPerMinute = 200;
    const wordCount = content.trim().split(/\s+/).length;
    const readingTime = Math.ceil(wordCount / wordsPerMinute);
    return `${readingTime} min de leitura`;
}

// ===== Copy Link Button =====
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Link copiado!');
        });
    } else {
        // Fallback
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('Link copiado!');
    }
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-gray-800 text-white px-6 py-3 rounded-lg shadow-lg transform translate-y-full transition-transform duration-300';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('translate-y-full');
    }, 100);
    
    setTimeout(() => {
        toast.classList.add('translate-y-full');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}