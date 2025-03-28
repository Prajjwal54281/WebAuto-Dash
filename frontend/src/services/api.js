import axios from 'axios';
import config, {
    API_ENDPOINTS,
    getApiHeaders,
    buildUrlWithCacheBust,
    apiLog
} from '../config/api';

// Create axios instance with centralized configuration
const api = axios.create({
    baseURL: config.API_BASE_URL,
    timeout: config.TIMEOUT,
    headers: getApiHeaders(),
});

// Simple cache for frequently accessed data
const cache = new Map();
const CACHE_DURATION = config.CACHE_DURATION;

// Clear cache completely on startup
cache.clear();

// Add a function to clear cache manually
export const clearApiCache = () => {
    cache.clear();
    apiLog('🧹 API cache cleared');
};

// Helper function to get cached data
const getCachedData = (key) => {
    const cached = cache.get(key);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        return cached.data;
    }
    // Remove expired cache entries
    cache.delete(key);
    return null;
};

// Helper function to set cached data
const setCachedData = (key, data) => {
    cache.set(key, {
        data,
        timestamp: Date.now()
    });
};

// Add request interceptor for debugging and cache-busting
api.interceptors.request.use(
    (requestConfig) => {
        apiLog('🚀 API Request:', `${requestConfig.method?.toUpperCase()} ${requestConfig.url}`, requestConfig.params);

        // Apply cache-busting headers from centralized config
        requestConfig.headers = {
            ...requestConfig.headers,
            ...getApiHeaders()
        };

        // Add cache busting to URL if in development
        requestConfig.url = buildUrlWithCacheBust(requestConfig.url);

        return requestConfig;
    },
    (error) => {
        apiLog('❌ API Request Error:', error);
        return Promise.reject(error);
    }
);

// Add response interceptor for error handling
api.interceptors.response.use(
    (response) => {
        apiLog('✅ API Response:', `${response.config.url} - Status: ${response.status}`,
            `Data keys: ${Object.keys(response.data || {}).join(', ')}`);
        return response;
    },
    async (error) => {
        const originalRequest = error.config;

        // Retry logic for timeout errors
        if (error.code === 'ECONNABORTED' && !originalRequest._retry) {
            originalRequest._retry = true;
            originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

            if (originalRequest._retryCount <= config.MAX_RETRIES) {
                apiLog(`🔄 Retrying request (${originalRequest._retryCount}/${config.MAX_RETRIES}):`, originalRequest.url);

                // Wait before retrying
                await new Promise(resolve => setTimeout(resolve, config.RETRY_DELAY));

                return api(originalRequest);
            }
        }

        apiLog('❌ API Response Error:',
            `${error.config?.url} - Status: ${error.response?.status}`,
            error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// API endpoints using centralized configuration
export const jobsApi = {
    create: (jobData) => api.post(API_ENDPOINTS.JOBS, jobData),
    getAll: async (page = 1, perPage = 20, noCacheHeaders = null) => {
        const cacheKey = `jobs-${page}-${perPage}`;

        // Skip cache if no-cache headers provided
        if (!noCacheHeaders) {
            const cached = getCachedData(cacheKey);
            if (cached) return { data: cached };
        }

        const requestConfig = noCacheHeaders ? {
            params: { page, per_page: perPage },
            headers: noCacheHeaders
        } : {
            params: { page, per_page: perPage }
        };

        const response = await api.get(API_ENDPOINTS.JOBS, requestConfig);

        // Only cache if not using no-cache headers
        if (!noCacheHeaders) {
            setCachedData(cacheKey, response.data);
        }
        return response;
    },
    getById: (id) => api.get(API_ENDPOINTS.JOB_BY_ID(id)),
    delete: (id) => api.delete(API_ENDPOINTS.JOB_DELETE(id)),
    confirmLogin: (id) => api.post(API_ENDPOINTS.JOB_CONFIRM_LOGIN(id)),
    getResumeAnalysis: (id) => api.get(`${API_ENDPOINTS.JOBS}/${id}/resume-analysis`),
    retryWithResume: (id, mode = 'resume') => api.post(`${API_ENDPOINTS.JOBS}/${id}/retry`, { mode }),
    getActive: async (noCacheHeaders = null) => {
        const cacheKey = 'active-jobs';

        // Skip cache if no-cache headers provided
        if (!noCacheHeaders) {
            const cached = getCachedData(cacheKey);
            if (cached) return { data: cached };
        }

        const requestConfig = noCacheHeaders ? { headers: noCacheHeaders } : {};
        const response = await api.get(API_ENDPOINTS.JOBS_ACTIVE, requestConfig);

        // Only cache if not using no-cache headers
        if (!noCacheHeaders) {
            setCachedData(cacheKey, response.data);
        }
        return response;
    }
};

export const adaptersApi = {
    getActive: async (noCacheHeaders = null) => {
        const cacheKey = 'active-adapters';

        // Skip cache if no-cache headers provided
        if (!noCacheHeaders) {
            const cached = getCachedData(cacheKey);
            if (cached) return { data: cached };
        }

        const requestConfig = noCacheHeaders ? {
            headers: noCacheHeaders
        } : {};

        const response = await api.get(API_ENDPOINTS.ADAPTERS, requestConfig);

        // Only cache if not using no-cache headers
        if (!noCacheHeaders) {
            setCachedData(cacheKey, response.data);
        }
        return response;
    },
    getAll: () => api.get(API_ENDPOINTS.ADAPTERS_ADMIN),
    create: (adapterData) => api.post(API_ENDPOINTS.ADAPTERS_ADMIN, adapterData),
    update: (id, adapterData) => api.put(API_ENDPOINTS.ADAPTER_BY_ID(id), adapterData),
    delete: (id) => api.delete(API_ENDPOINTS.ADAPTER_BY_ID(id)),
    getAvailableScripts: () => api.get(API_ENDPOINTS.ADAPTER_SCRIPTS),

    // Check if adapter file exists in backend filesystem
    checkFileExists: async (filename) => {
        try {
            const response = await api.get(`/admin/adapters/check-file/${encodeURIComponent(filename)}`);
            return response;
        } catch (error) {
            apiLog('❌ Check file exists error:', error);
            // Return a default response indicating file doesn't exist if endpoint fails
            if (error.response?.status === 404) {
                return { data: { exists: false } };
            }
            throw error;
        }
    },

    // Force delete adapter (with proper job handling)
    forceDelete: async (id) => {
        try {
            const response = await api.delete(`/admin/adapters/${id}/force-delete`);
            return response;
        } catch (error) {
            apiLog('❌ Force delete adapter error:', error);
            throw error;
        }
    },

    // Check if adapter has dependent jobs
    checkDependentJobs: async (id) => {
        try {
            const response = await api.get(`/admin/adapters/${id}/dependent-jobs`);
            return response;
        } catch (error) {
            apiLog('❌ Check dependent jobs error:', error);
            // Return no dependencies if endpoint fails
            if (error.response?.status === 404) {
                return { data: { has_dependencies: false, job_count: 0 } };
            }
            throw error;
        }
    }
};

export const adminApi = {
    validateScript: (scriptFilename) => api.get(API_ENDPOINTS.ADAPTER_VALIDATE(scriptFilename)),
    getSystemStats: () => api.get('/admin/stats'),
    getSystemLogs: () => api.get('/admin/logs'),
    clearLogs: () => api.delete('/admin/logs'),
    getAdapters: () => api.get('/admin/adapters'),
    createAdapter: (data) => api.post('/admin/adapters', data),
    updateAdapter: (id, data) => api.put(`/admin/adapters/${id}`, data),
    deleteAdapter: (id) => api.delete(`/admin/adapters/${id}`),
    activateAdapter: (id) => api.post(`/admin/adapters/${id}/activate`),
    deactivateAdapter: (id) => api.post(`/admin/adapters/${id}/deactivate`),
};

// Portal Inspector API - Complete implementation
export const portalInspectorApi = {
    analyzePortal: (config) => api.post('/portal-inspector/analyze', config),
    quickAnalyzePortal: (config) => api.post('/portal-inspector/quick-analyze', config),
    getSavedAnalyses: () => api.get('/portal-inspector/saved-analyses'),
    getAnalysisDetails: (id) => api.get(`/portal-inspector/analysis/${id}`),
    testSelector: (data) => api.post('/portal-inspector/test-selector', data),
    generateAdapter: (data) => api.post('/portal-inspector/generate-adapter', data),
    getPortalAdapters: () => api.get('/portal-inspector/adapters'),
    checkAdapterJobs: (adapterId) => api.get(`/portal-inspector/check-adapter-jobs/${adapterId}`),
    deleteAdapter: (adapterId) => api.post('/portal-inspector/delete-adapter', { adapter_id: adapterId }),
    createMediMind2: () => api.post('/portal-inspector/create-medimind2'),
    getSystemStatus: () => api.get('/portal-inspector/status'),
    syncAdapters: () => api.post('/portal-inspector/sync-adapters'),
};

// Real-time API
export const realtimeApi = {
    getJobProgress: (jobId) => api.get(`/realtime/job-progress/${jobId}`),
    retryJob: (jobId) => api.post(`/realtime/job/${jobId}/retry`),
    cancelJob: (jobId) => api.post(`/realtime/jobs/cancel/${jobId}`),
    createBatchJobs: (batchData) => api.post('/realtime/jobs/batch', batchData),
    getSystemStats: () => api.get('/realtime/system/stats'),
    healthCheckJobs: () => api.post('/realtime/jobs/health-check'),
    getActiveJobs: () => api.get('/realtime/active-jobs'),
    getJobHistory: () => api.get('/realtime/job-history'),
};

// Live Inspector v2 API - Advanced live portal inspection
export const liveInspectorApi = {
    startInspection: (config) => api.post('/live-inspector/live-inspect-v2', config),
    stopInspection: (inspectionId) => api.post(`/live-inspector/live-inspect-v2/${inspectionId}/stop`),
    getInspectionStatus: (inspectionId) => api.get(`/live-inspector/live-inspect-v2/${inspectionId}/status`),
    downloadInspectionResults: (inspectionId) => api.get(`/live-inspector/live-inspect-v2/${inspectionId}/download`),
    getCapabilities: () => api.get('/live-inspector/live-inspect-v2/capabilities'),
    healthCheck: () => api.get('/live-inspector/healthz'),
};

export default api; 