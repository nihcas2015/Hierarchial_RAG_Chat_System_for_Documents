// Get DOM elements
const resetForm = document.getElementById('resetForm');
const emailInput = document.getElementById('email');
const resetBtn = document.getElementById('resetBtn');
const errorMessage = document.getElementById('errorMessage');
const resetInfo = document.getElementById('resetInfo');

// API endpoint
const API_RESET = 'http://localhost:5000/api/forgot-password';

// Check if user is already logged in
window.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');
    if (token) {
        window.location.href = 'dashboard.html';
    }
});

// Handle form submission
resetForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = emailInput.value.trim();

    // Validate email
    if (!email) {
        showError('Please enter your email address');
        return;
    }

    if (!isValidEmail(email)) {
        showError('Please enter a valid email address');
        return;
    }

    // Show loading state
    setLoading(true);
    errorMessage.style.display = 'none';
    resetInfo.style.display = 'none';

    try {
        const response = await fetch(API_RESET, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showSuccess('Password reset link sent to your email!');
            resetForm.reset();
        } else {
            showError(data.message || 'Unable to process your request. Please try again.');
        }
    } catch (error) {
        console.error('Reset error:', error);
        showError('Connection failed. Please check your internet and try again.');
    } finally {
        setLoading(false);
    }
});

// Clear error when user starts typing
emailInput.addEventListener('input', () => {
    if (errorMessage.style.display === 'block') {
        errorMessage.style.display = 'none';
    }
});

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    resetInfo.style.display = 'none';
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Show success message
function showSuccess(message) {
    resetInfo.textContent = message;
    resetInfo.style.display = 'block';
    errorMessage.style.display = 'none';
    resetInfo.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Set loading state
function setLoading(isLoading) {
    resetBtn.disabled = isLoading;
    
    if (isLoading) {
        resetBtn.classList.add('loading');
        resetBtn.querySelector('span').textContent = 'Sending...';
    } else {
        resetBtn.classList.remove('loading');
        resetBtn.querySelector('span').textContent = 'Send Reset Link';
    }
}

// Helper function to validate email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}
