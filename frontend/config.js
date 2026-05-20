// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

export const API_ENDPOINTS = {
    LOGIN: `${API_BASE_URL}/login`,
    SIGNUP: `${API_BASE_URL}/signup`,
    VERIFY_TOKEN: `${API_BASE_URL}/verify-token`,
    LOGOUT: `${API_BASE_URL}/logout`,
    GET_DOCUMENTS: `${API_BASE_URL}/documents`,
    UPLOAD_DOCUMENT: `${API_BASE_URL}/documents/upload`,
    SEND_MESSAGE: `${API_BASE_URL}/messages/send`,
    GET_CONVERSATIONS: `${API_BASE_URL}/conversations`
};

export default API_BASE_URL;
