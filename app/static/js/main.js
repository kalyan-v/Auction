// Main JavaScript file
console.log('Player Auction System loaded');

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
