/**
 * API Configuration for WebAutoDash
 * Single source of truth for all API endpoints and configuration
 */

// Environment-based configuration
const config = {
    // API Base URL - uses environment variable or fallback
    API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:5005/api',

    // Frontend URL for CORS and redirects
    FRONTEND_URL: process.env.REACT_APP_FRONTEND_URL || 'http://localhost:3009',

    // App configuration
    APP_NAME: process.env.REACT_APP_APP_NAME || 'WebAutoDash',
    VERSION: process.env.REACT_APP_VERSION || '1.0.0',

    // Environment detection
    IS_DEVELOPMENT: process.env.NODE_ENV === 'development',
    IS_PRODUCTION: process.env.NODE_ENV === 'production',

    // API Configuration
    TIMEOUT: 30000, // 30 seconds - increased from 10 seconds
    CACHE_DURATION: 5000, // 5 seconds for development - increased from 1 second

    // Retry configuration
    MAX_RETRIES: 3,
    RETRY_DELAY: 2000, // 2 seconds between retries
};

// Dynamic API endpoint builder
export const buildApiUrl = (endpoint) => {
    // Remove leading slash if present
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `${config.API_BASE_URL}/${cleanEndpoint}`;
};

// API Endpoints - centralized endpoint definitions
export const API_ENDPOINTS = {
    // Jobs
    JOBS: '/jobs',
    JOBS_ACTIVE: '/jobs/active',
    JOB_BY_ID: (id) => `/jobs/${id}`,
    JOB_DELETE: (id) => `/jobs/${id}`,
    JOB_CONFIRM_LOGIN: (id) => `/jobs/${id}/confirm_login`,

    // Adapters
    ADAPTERS: '/adapters',
    ADAPTERS_ADMIN: '/admin/adapters',
    ADAPTER_BY_ID: (id) => `/admin/adapters/${id}`,
    ADAPTER_SCRIPTS: '/admin/adapters/available_scripts',
    ADAPTER_VALIDATE: (filename) => `/admin/adapters/validate_script/${filename}`,

    // Health and Status
    HEALTH: '/health',
    STATUS: '/',
};

// Headers for API requests
export const getApiHeaders = (additionalHeaders = {}) => {
    const baseHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    };

    // Add cache-busting headers for development
    if (config.IS_DEVELOPMENT) {
        baseHeaders['Cache-Control'] = 'no-cache, no-store, must-revalidate';
        baseHeaders['Pragma'] = 'no-cache';
        baseHeaders['Expires'] = '0';
        baseHeaders['X-Requested-With'] = 'XMLHttpRequest';
        baseHeaders['X-Cache-Bust'] = Date.now().toString();
    }

    return { ...baseHeaders, ...additionalHeaders };
};

// URL builder with cache busting for development
export const buildUrlWithCacheBust = (url) => {
    if (!config.IS_DEVELOPMENT) return url;

    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}_t=${Date.now()}`;
};

// Logging utility
export const apiLog = (message, data = null) => {
    if (config.IS_DEVELOPMENT) {
        console.log(`[API] ${message}`, data || '');
    }
};

// Export default configuration
export default config; 