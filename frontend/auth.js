// Authentication Utilities

export const auth = {
    // Set auth token in localStorage
    setToken(token) {
        localStorage.setItem('authToken', token);
    },

    // Get auth token from localStorage
    getToken() {
        return localStorage.getItem('authToken');
    },

    // Check if user is authenticated
    isAuthenticated() {
        return !!localStorage.getItem('authToken');
    },

    // Remove auth token (logout)
    removeToken() {
        localStorage.removeItem('authToken');
    },

    // Get auth header for API requests
    getAuthHeader() {
        const token = this.getToken();
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }
};

export default auth;
