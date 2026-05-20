// Get DOM elements
const signupForm = document.getElementById('signupForm');
const fullnameInput = document.getElementById('fullname');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const confirmPasswordInput = document.getElementById('confirmPassword');
const termsCheckbox = document.getElementById('terms');
const signupBtn = document.getElementById('signupBtn');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');
const passwordStrength = document.getElementById('passwordStrength');

// API endpoint
const API_SIGNUP = 'http://localhost:5000/api/signup';

// Check if user is already logged in
window.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');
    if (token) {
        window.location.href = 'dashboard.html';
    }
});

// Handle form submission
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fullname = fullnameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    // Validate inputs
    if (!fullname || !email || !password || !confirmPassword) {
        showError('Please fill in all fields');
        return;
    }

    if (!isValidEmail(email)) {
        showError('Please enter a valid email address');
        return;
    }

    if (password.length < 8) {
        showError('Password must be at least 8 characters long');
        return;
    }

    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return;
    }

    if (!termsCheckbox.checked) {
        showError('Please agree to the Terms of Service');
        return;
    }

    // Show loading state
    setLoading(true);
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';

    try {
        const response = await fetch(API_SIGNUP, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fullname,
                email,
                password
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Show success message
            showSuccess('Account created successfully! Redirecting to login...');
            
            // Redirect to login after 2 seconds
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 2000);
        } else {
            showError(data.message || 'Signup failed. Please try again.');
        }
    } catch (error) {
        console.error('Signup error:', error);
        showError('Connection failed. Please check your internet and try again.');
    } finally {
        setLoading(false);
    }
});

// Real-time password strength indicator
passwordInput.addEventListener('input', () => {
    const password = passwordInput.value;
    const strength = calculatePasswordStrength(password);

    passwordStrength.className = 'password-strength ' + strength;

    // Clear error when user starts typing
    if (errorMessage.style.display === 'block') {
        errorMessage.style.display = 'none';
    }
});

// Real-time email validation
emailInput.addEventListener('blur', () => {
    if (emailInput.value && !isValidEmail(emailInput.value)) {
        emailInput.style.borderColor = '#f44336';
    } else {
        emailInput.style.borderColor = '';
    }
});

// Check password match in real-time
confirmPasswordInput.addEventListener('input', () => {
    if (passwordInput.value && confirmPasswordInput.value !== passwordInput.value) {
        confirmPasswordInput.style.borderColor = '#f44336';
    } else {
        confirmPasswordInput.style.borderColor = '';
    }
});

// Clear error when user starts typing
fullnameInput.addEventListener('input', clearError);
emailInput.addEventListener('input', clearError);

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    successMessage.style.display = 'none';
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Show success message
function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.style.display = 'block';
    errorMessage.style.display = 'none';
    successMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Clear error message
function clearError() {
    if (errorMessage.style.display === 'block') {
        errorMessage.style.display = 'none';
    }
}

// Set loading state
function setLoading(isLoading) {
    signupBtn.disabled = isLoading;
    
    if (isLoading) {
        signupBtn.classList.add('loading');
        signupBtn.querySelector('span').textContent = 'Creating Account...';
    } else {
        signupBtn.classList.remove('loading');
        signupBtn.querySelector('span').textContent = 'Create Account';
    }
}

// Calculate password strength
function calculatePasswordStrength(password) {
    if (!password) return '';
    
    let strength = 0;
    
    // Length check
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    
    // Character variety
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;
    
    if (strength <= 2) return 'weak';
    if (strength <= 4) return 'medium';
    return 'strong';
}

// Helper function to validate email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}
