// Get DOM elements
const logoutBtn = document.getElementById('logoutBtn');
const userEmailElement = document.getElementById('userEmail');
const navItems = document.querySelectorAll('.nav-item');
const pageTitle = document.getElementById('pageTitle');
const pages = document.querySelectorAll('.page');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.querySelector('.send-btn');
const chatMessages = document.getElementById('chatMessages');
const uploadBtn = document.getElementById('uploadBtn');
const uploadDocBtn = document.getElementById('uploadDocBtn');
const fileInput = document.getElementById('fileInput');
const modalFileInput = document.getElementById('modalFileInput');
const uploadModal = document.getElementById('uploadModal');
const confirmUploadBtn = document.getElementById('confirmUploadBtn');
const fileUploadArea = document.getElementById('fileUploadArea');
const fileNameDisplay = document.getElementById('fileName');
const documentsList = document.getElementById('documentsList');
const mobileMenuOpen = document.getElementById('mobileMenuOpen');
const mobileMenuClose = document.getElementById('mobileMenuClose');
const sidebar = document.querySelector('.sidebar');

// API endpoints
const API_BASE = 'http://localhost:5000/api';

// Check authentication
window.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    // Display user email
    const userEmail = localStorage.getItem('userEmail');
    if (userEmail) {
        userEmailElement.textContent = userEmail;
    }

    // Load documents
    loadDocuments();
});

// Logout
logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('userEmail');
    window.location.href = 'login.html';
});

// Navigation
navItems.forEach(item => {
    item.addEventListener('click', () => {
        const pageName = item.dataset.page;
        
        // Update active nav item
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

        // Update active page
        pages.forEach(page => page.classList.remove('active'));
        document.getElementById(pageName + 'Page').classList.add('active');

        // Update page title
        pageTitle.textContent = item.textContent.trim();

        // Close mobile menu
        sidebar.classList.remove('active');
    });
});

// Mobile menu toggle
mobileMenuOpen.addEventListener('click', () => {
    sidebar.classList.add('active');
});

mobileMenuClose.addEventListener('click', () => {
    sidebar.classList.remove('active');
});

// Chat form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (!message) return;

    // Display user message
    const userMessageDiv = document.createElement('div');
    userMessageDiv.className = 'message user-message';
    userMessageDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
    chatMessages.appendChild(userMessageDiv);

    messageInput.value = '';
    sendBtn.disabled = true;
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`${API_BASE}/messages/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        if (response.ok) {
            // Display assistant response
            const assistantMessageDiv = document.createElement('div');
            assistantMessageDiv.className = 'message assistant-message';
            assistantMessageDiv.innerHTML = `<p>${escapeHtml(data.response)}</p>`;
            chatMessages.appendChild(assistantMessageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            showChatError('Failed to send message');
        }
    } catch (error) {
        console.error('Error:', error);
        showChatError('Connection error. Please try again.');
    } finally {
        sendBtn.disabled = false;
        messageInput.focus();
    }
});

// Message input enable/disable send button
messageInput.addEventListener('input', () => {
    sendBtn.disabled = messageInput.value.trim() === '';
});

// Upload button
uploadBtn.addEventListener('click', () => {
    fileInput.click();
});

uploadDocBtn.addEventListener('click', () => {
    uploadModal.classList.add('active');
});

// Modal close buttons
document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const modalId = e.target.dataset.close;
        document.getElementById(modalId).classList.remove('active');
    });
});

// File upload modal
selectFileBtn = document.getElementById('selectFileBtn');
if (selectFileBtn) {
    selectFileBtn.addEventListener('click', () => {
        modalFileInput.click();
    });
}

// Drag and drop
fileUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileUploadArea.classList.add('dragover');
});

fileUploadArea.addEventListener('dragleave', () => {
    fileUploadArea.classList.remove('dragover');
});

fileUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    fileUploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        modalFileInput.files = files;
        confirmUploadBtn.disabled = false;
    }
});

// File selection
modalFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        confirmUploadBtn.disabled = false;
    }
});

// Confirm upload
confirmUploadBtn.addEventListener('click', async () => {
    if (!modalFileInput.files.length) return;

    const file = modalFileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    // Show progress
    fileUploadArea.style.display = 'none';
    document.getElementById('uploadProgress').style.display = 'block';

    try {
        const token = localStorage.getItem('authToken');
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                document.getElementById('progressFill').style.width = percentComplete + '%';
                document.getElementById('uploadStatus').textContent = 
                    `Uploading... ${Math.round(percentComplete)}%`;
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                document.getElementById('uploadStatus').textContent = 'Upload complete!';
                
                setTimeout(() => {
                    uploadModal.classList.remove('active');
                    loadDocuments();
                    resetUploadModal();
                }, 1000);
            } else {
                showUploadError('Upload failed');
                resetUploadModal();
            }
        });

        xhr.addEventListener('error', () => {
            showUploadError('Upload error');
            resetUploadModal();
        });

        xhr.open('POST', `${API_BASE}/documents/upload`);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.send(formData);
    } catch (error) {
        console.error('Upload error:', error);
        showUploadError('Upload failed');
        resetUploadModal();
    }
});

// Load documents
async function loadDocuments() {
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`${API_BASE}/documents`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok && data.documents.length > 0) {
            documentsList.innerHTML = '';
            data.documents.forEach(doc => {
                const docCard = document.createElement('div');
                docCard.className = 'document-card';
                docCard.innerHTML = `
                    <div class="document-icon">📄</div>
                    <div class="document-name">${escapeHtml(doc.file_name)}</div>
                    <div class="document-date">${new Date(doc.uploaded_at).toLocaleDateString()}</div>
                `;
                documentsList.appendChild(docCard);
            });
        }
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

// Helper functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showChatError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message error-message';
    errorDiv.innerHTML = `<p>${message}</p>`;
    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showUploadError(message) {
    alert(message);
}

function resetUploadModal() {
    modalFileInput.value = '';
    confirmUploadBtn.disabled = true;
    fileUploadArea.style.display = '';
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
}
