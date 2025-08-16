/**
 * Main JavaScript for Academic Reference Graph
 */

// Global variables
let currentUser = null;
let notifications = [];

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadUserPreferences();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('Initializing Academic Reference Graph...');
    
    // Check if user is authenticated
    checkAuthentication();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize modals
    initializeModals();
    
    // Setup search functionality
    setupSearch();
    
    // Load initial data
    loadInitialData();
}

/**
 * Setup global event listeners
 */
function setupEventListeners() {
    // Global search
    const searchForm = document.querySelector('form[action*="search"]');
    if (searchForm) {
        searchForm.addEventListener('submit', handleGlobalSearch);
    }
    
    // Notification close buttons
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-close')) {
            const alert = e.target.closest('.alert');
            if (alert) {
                alert.remove();
            }
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Window resize handling
    window.addEventListener('resize', handleWindowResize);
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize Bootstrap modals
 */
function initializeModals() {
    const modalTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="modal"]'));
    modalTriggerList.map(function (modalTriggerEl) {
        return new bootstrap.Modal(modalTriggerEl);
    });
}

/**
 * Setup search functionality
 */
function setupSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        // Debounced search
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 300);
        });
    }
}

/**
 * Perform search with debouncing
 */
function performSearch(query) {
    if (query.length < 2) return;
    
    // Show loading state
    showSearchLoading();
    
    // Perform search
    fetch(`/api/papers/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data);
        })
        .catch(error => {
            console.error('Search error:', error);
            hideSearchLoading();
        });
}

/**
 * Display search results
 */
function displaySearchResults(results) {
    hideSearchLoading();
    
    // This would be implemented based on the current page context
    console.log('Search results:', results);
}

/**
 * Show search loading state
 */
function showSearchLoading() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.classList.add('loading');
        searchInput.disabled = true;
    }
}

/**
 * Hide search loading state
 */
function hideSearchLoading() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.classList.remove('loading');
        searchInput.disabled = false;
    }
}

/**
 * Handle global search form submission
 */
function handleGlobalSearch(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const query = formData.get('search');
    
    if (query.trim()) {
        window.location.href = `/reference_graph/?search=${encodeURIComponent(query)}`;
    }
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[name="search"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            const modal = bootstrap.Modal.getInstance(openModal);
            if (modal) {
                modal.hide();
            }
        }
    }
}

/**
 * Handle window resize
 */
function handleWindowResize() {
    // Adjust layout for mobile devices
    if (window.innerWidth <= 768) {
        document.body.classList.add('mobile-view');
    } else {
        document.body.classList.remove('mobile-view');
    }
}

/**
 * Check user authentication status
 */
function checkAuthentication() {
    // This would check if user is logged in
    // For now, we'll assume anonymous access
    currentUser = null;
}

/**
 * Load user preferences
 */
function loadUserPreferences() {
    const preferences = localStorage.getItem('userPreferences');
    if (preferences) {
        try {
            const prefs = JSON.parse(preferences);
            applyUserPreferences(prefs);
        } catch (error) {
            console.error('Error loading user preferences:', error);
        }
    }
}

/**
 * Apply user preferences
 */
function applyUserPreferences(preferences) {
    // Apply theme
    if (preferences.theme) {
        document.body.setAttribute('data-theme', preferences.theme);
    }
    
    // Apply font size
    if (preferences.fontSize) {
        document.documentElement.style.fontSize = preferences.fontSize;
    }
}

/**
 * Save user preferences
 */
function saveUserPreferences(preferences) {
    try {
        localStorage.setItem('userPreferences', JSON.stringify(preferences));
    } catch (error) {
        console.error('Error saving user preferences:', error);
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notification = {
        id: Date.now(),
        message,
        type,
        timestamp: new Date()
    };
    
    notifications.push(notification);
    displayNotification(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        removeNotification(notification.id);
    }, duration);
}

/**
 * Display notification
 */
function displayNotification(notification) {
    const container = document.querySelector('.messages') || document.body;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${notification.type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${notification.message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(alertDiv);
    
    // Trigger fade in animation
    setTimeout(() => {
        alertDiv.classList.add('show');
    }, 100);
}

/**
 * Remove notification
 */
function removeNotification(id) {
    const index = notifications.findIndex(n => n.id === id);
    if (index > -1) {
        notifications.splice(index, 1);
    }
    
    // Remove from DOM
    const alertElement = document.querySelector(`[data-notification-id="${id}"]`);
    if (alertElement) {
        alertElement.remove();
    }
}

/**
 * Load initial data
 */
function loadInitialData() {
    // Load paper statistics if on home page
    if (window.location.pathname === '/') {
        loadPaperStatistics();
    }
}

/**
 * Load paper statistics
 */
function loadPaperStatistics() {
    fetch('/api/papers/statistics/')
        .then(response => response.json())
        .then(data => {
            updateStatisticsDisplay(data);
        })
        .catch(error => {
            console.error('Error loading statistics:', error);
        });
}

/**
 * Update statistics display
 */
function updateStatisticsDisplay(stats) {
    // Update statistics cards
    const elements = {
        'total_papers': document.getElementById('total_papers'),
        'total_references': document.getElementById('total_references'),
        'total_authors': document.getElementById('total_authors'),
        'total_citations': document.getElementById('total_citations')
    };
    
    Object.keys(elements).forEach(key => {
        const element = elements[key];
        if (element && stats[key] !== undefined) {
            element.textContent = stats[key];
        }
    });
}

/**
 * Utility function to format dates
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Utility function to format file sizes
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Utility function to truncate text
 */
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Utility function to debounce function calls
 */
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

/**
 * Utility function to throttle function calls
 */
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

/**
 * Export functions for global use
 */
window.ReferenceGraph = {
    showNotification,
    formatDate,
    formatFileSize,
    truncateText,
    debounce,
    throttle
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showNotification,
        formatDate,
        formatFileSize,
        truncateText,
        debounce,
        throttle
    };
}
