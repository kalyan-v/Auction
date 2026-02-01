// Main JavaScript file - WPL Auction System
// Utility functions shared across all pages

// CSRF Protection - Get token from meta tag
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Secure fetch wrapper that automatically includes CSRF token for non-GET requests
async function secureFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();

    // Add CSRF token for state-changing requests
    if (method !== 'GET' && method !== 'HEAD') {
        options.headers = {
            ...options.headers,
            'X-CSRFToken': getCSRFToken()
        };
    }

    return fetch(url, options);
}

// Utility function to escape HTML to prevent XSS
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Utility function to format currency in Indian Rupees (Lakhs/Crores)
function formatCurrency(amount) {
    if (amount >= 10000000) {
        // Show in Crores
        return '₹' + (amount / 10000000).toFixed(2) + ' Cr';
    } else if (amount >= 100000) {
        // Show in Lakhs
        return '₹' + (amount / 100000).toFixed(0) + ' L';
    } else {
        return '₹' + amount.toLocaleString('en-IN');
    }
}

// Show notification - uses CSS classes from style.css for styling
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.setAttribute('role', 'alert');
    notification.setAttribute('aria-live', 'polite');

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Note: Notification animations are defined in style.css
