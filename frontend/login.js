// Get DOM elements
const loginForm = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const errorMessage = document.getElementById('errorMessage');

// API endpoint
const API_LOGIN = 'http://localhost:5000/api/login';

// Check if user is already logged in
window.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');
    if (token) {
        window.location.href = 'dashboard.html';
    }
});

// Handle form submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    // Validate inputs
    if (!email || !password) {
        showError('Please fill in all fields');
        return;
    }

    if (!isValidEmail(email)) {
        showError('Please enter a valid email address');
        return;
    }

    // Show loading state
    setLoading(true);
    errorMessage.style.display = 'none';

    try {
        const response = await fetch(API_LOGIN, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Save token and user info
            localStorage.setItem('authToken', data.token);
            localStorage.setItem('userId', data.userId);
            localStorage.setItem('userEmail', data.email);

            // Show success animation and redirect
            loginBtn.textContent = '✓ Login Successful!';
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1000);
        } else {
            showError(data.message || 'Invalid email or password');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Connection failed. Please check your internet and try again.');
    } finally {
        setLoading(false);
    }
});

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Set loading state
function setLoading(isLoading) {
    loginBtn.disabled = isLoading;
    
    if (isLoading) {
        loginBtn.classList.add('loading');
        loginBtn.querySelector('span').textContent = 'Logging in...';
    } else {
        loginBtn.classList.remove('loading');
        loginBtn.querySelector('span').textContent = 'Login';
    }
}

// Real-time validation
emailInput.addEventListener('blur', () => {
    if (emailInput.value && !isValidEmail(emailInput.value)) {
        emailInput.style.borderColor = '#f44336';
    } else {
        emailInput.style.borderColor = '';
    }
});

// Clear error when user starts typing
emailInput.addEventListener('input', () => {
    if (errorMessage.style.display === 'block') {
        errorMessage.style.display = 'none';
    }
});

passwordInput.addEventListener('input', () => {
    if (errorMessage.style.display === 'block') {
        errorMessage.style.display = 'none';
    }
});

// Helper function to validate email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}