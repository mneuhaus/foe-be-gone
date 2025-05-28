// API utility functions for handling base URL in Home Assistant ingress

// Get base URL from meta tag
const BASE_URL = document.querySelector('meta[name="base-url"]')?.content || '';

// Helper function to construct API URLs
function apiUrl(path) {
    // Ensure path starts with /
    if (!path.startsWith('/')) {
        path = '/' + path;
    }
    return BASE_URL + path;
}

// Helper function for fetch with base URL
async function apiFetch(path, options = {}) {
    return fetch(apiUrl(path), options);
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { apiUrl, apiFetch, BASE_URL };
}