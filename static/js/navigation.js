/**
 * Navigation and Theme Management
 * Handles sidebar toggle, theme switching, and persistence
 */

(function() {
    'use strict';

    // DOM Elements
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const themeButtons = document.querySelectorAll('.theme-btn');
    const body = document.body;
    const html = document.documentElement;

    // State
    let sidebarCollapsed = false;
    let currentTheme = 'harmandir';

    // Initialize
    function init() {
        loadTheme();
        loadSidebarState();
        setupEventListeners();
        updateActiveNavItem();
    }

    // Load theme from localStorage or system preference
    function loadTheme() {
        const savedTheme = localStorage.getItem('katha-theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (savedTheme) {
            currentTheme = savedTheme;
        } else if (systemPrefersDark) {
            currentTheme = 'midnight';
        }
        
        applyTheme(currentTheme);
    }

    // Apply theme to document
    function applyTheme(theme) {
        html.setAttribute('data-theme', theme);
        currentTheme = theme;
        localStorage.setItem('katha-theme', theme);
        
        // Update active button
        themeButtons.forEach(btn => {
            if (btn.dataset.theme === theme) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    // Load sidebar state from localStorage
    function loadSidebarState() {
        const savedState = localStorage.getItem('katha-sidebar-collapsed');
        if (savedState === 'true') {
            sidebarCollapsed = true;
            sidebar.classList.add('collapsed');
        }
    }

    // Save sidebar state
    function saveSidebarState() {
        localStorage.setItem('katha-sidebar-collapsed', sidebarCollapsed);
    }

    // Toggle sidebar
    function toggleSidebar() {
        sidebarCollapsed = !sidebarCollapsed;
        
        if (sidebarCollapsed) {
            sidebar.classList.add('collapsed');
        } else {
            sidebar.classList.remove('collapsed');
        }
        
        saveSidebarState();
    }

    // Setup event listeners
    function setupEventListeners() {
        // Sidebar toggle
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', toggleSidebar);
        }

        // Theme buttons
        themeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const theme = btn.dataset.theme;
                applyTheme(theme);
            });
        });

        // Mobile: Close sidebar when clicking outside
        if (window.innerWidth <= 1024) {
            document.addEventListener('click', (e) => {
                if (sidebar && !sidebar.contains(e.target) && 
                    sidebarToggle && !sidebarToggle.contains(e.target)) {
                    if (sidebar.classList.contains('open')) {
                        sidebar.classList.remove('open');
                    }
                }
            });
        }

        // Handle window resize
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                handleResize();
                setupMobileMenu();
            }, 250);
        });

        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', (e) => {
            // Only auto-switch if user hasn't manually set a preference
            if (!localStorage.getItem('katha-theme')) {
                applyTheme(e.matches ? 'midnight' : 'harmandir');
            }
        });
    }

    // Handle window resize
    function handleResize() {
        if (window.innerWidth <= 1024) {
            // Mobile: sidebar should be hidden by default
            sidebar.classList.remove('collapsed');
            if (!sidebar.classList.contains('open')) {
                sidebar.style.transform = 'translateX(-100%)';
            }
        } else {
            // Desktop: restore sidebar state
            sidebar.style.transform = '';
            if (sidebarCollapsed) {
                sidebar.classList.add('collapsed');
            } else {
                sidebar.classList.remove('collapsed');
            }
        }
    }

    // Update active navigation item based on current page
    function updateActiveNavItem() {
        const currentPath = window.location.pathname;
        const navItems = document.querySelectorAll('.nav-item');
        
        navItems.forEach(item => {
            item.classList.remove('active');
            const href = item.getAttribute('href');
            if (href && (currentPath === href || currentPath === href + '/')) {
                item.classList.add('active');
            }
        });
    }

    // Create backdrop overlay
    function createBackdrop() {
        if (!document.getElementById('sidebarBackdrop')) {
            const backdrop = document.createElement('div');
            backdrop.id = 'sidebarBackdrop';
            backdrop.className = 'sidebar-backdrop';
            backdrop.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                z-index: 999;
                display: none;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            backdrop.addEventListener('click', () => {
                sidebar.classList.remove('open');
            });
            document.body.appendChild(backdrop);
        }
        return document.getElementById('sidebarBackdrop');
    }

    // Update backdrop visibility
    function updateBackdrop() {
        const backdrop = createBackdrop();
        if (window.innerWidth <= 1024 && sidebar.classList.contains('open')) {
            backdrop.style.display = 'block';
            setTimeout(() => {
                backdrop.style.opacity = '1';
            }, 10);
        } else {
            backdrop.style.opacity = '0';
            setTimeout(() => {
                backdrop.style.display = 'none';
            }, 300);
        }
    }

    // Mobile menu toggle (for hamburger menu on mobile)
    function setupMobileMenu() {
        if (window.innerWidth <= 1024) {
            // Create mobile menu button if it doesn't exist
            if (!document.getElementById('mobileMenuBtn')) {
                const mobileBtn = document.createElement('button');
                mobileBtn.id = 'mobileMenuBtn';
                mobileBtn.className = 'mobile-menu-btn';
                mobileBtn.setAttribute('aria-label', 'Toggle menu');
                mobileBtn.innerHTML = `
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="3" y1="6" x2="21" y2="6"></line>
                        <line x1="3" y1="12" x2="21" y2="12"></line>
                        <line x1="3" y1="18" x2="21" y2="18"></line>
                    </svg>
                `;
                mobileBtn.addEventListener('click', () => {
                    sidebar.classList.toggle('open');
                    updateBackdrop();
                });
                document.body.appendChild(mobileBtn);
            }
            
            // Watch for sidebar open/close changes
            const observer = new MutationObserver(() => {
                updateBackdrop();
            });
            observer.observe(sidebar, { attributes: true, attributeFilter: ['class'] });
        } else {
            // Remove mobile button on desktop
            const mobileBtn = document.getElementById('mobileMenuBtn');
            if (mobileBtn) {
                mobileBtn.remove();
            }
            const backdrop = document.getElementById('sidebarBackdrop');
            if (backdrop) {
                backdrop.remove();
            }
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            init();
            setupMobileMenu();
        });
    } else {
        init();
        setupMobileMenu();
    }

    // Export for external use
    window.KathaNavigation = {
        setTheme: applyTheme,
        getTheme: () => currentTheme,
        toggleSidebar: toggleSidebar
    };

})();
