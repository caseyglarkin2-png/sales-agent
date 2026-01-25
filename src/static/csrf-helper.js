/**
 * CSRF Token Helper for CaseyOS
 * Automatically fetches and manages CSRF tokens for all fetch() calls
 * 
 * Usage:
 *   <script src="/static/csrf-helper.js"></script>
 *   
 *   // Tokens are automatically injected into fetch() calls
 *   await fetch('/api/endpoint', { method: 'POST', body: ... });
 */

(function() {
    'use strict';

    // Global CSRF token storage
    let csrfToken = null;

    /**
     * Fetch CSRF token from server
     * Token is returned in X-CSRF-Token response header
     */
    async function fetchCSRFToken() {
        try {
            const response = await fetch('/health');
            const token = response.headers.get('X-CSRF-Token');
            if (token) {
                csrfToken = token;
                console.log('[CSRF] Token fetched successfully');
                return token;
            } else {
                console.warn('[CSRF] No token in response headers');
            }
        } catch (error) {
            console.error('[CSRF] Failed to fetch token:', error);
        }
        return null;
    }

    /**
     * Get current CSRF token (fetch if needed)
     */
    async function getCSRFToken() {
        if (!csrfToken) {
            await fetchCSRFToken();
        }
        return csrfToken;
    }

    /**
     * Refresh CSRF token
     * Call this if you receive a 403 CSRF error
     */
    async function refreshCSRFToken() {
        csrfToken = null;
        return await fetchCSRFToken();
    }

    /**
     * Wrap native fetch to automatically inject CSRF tokens
     */
    const originalFetch = window.fetch;
    window.fetch = async function(url, options = {}) {
        // Only inject CSRF for state-changing methods
        const method = (options.method || 'GET').toUpperCase();
        const needsCSRF = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

        if (needsCSRF) {
            // Ensure token is available
            const token = await getCSRFToken();
            if (token) {
                // Inject CSRF token header
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('X-CSRF-Token', token);
                } else {
                    options.headers['X-CSRF-Token'] = token;
                }
                console.log(`[CSRF] Injected token for ${method} ${url}`);
            } else {
                console.warn(`[CSRF] No token available for ${method} ${url}`);
            }
        }

        // Call original fetch
        const response = await originalFetch(url, options);

        // Auto-refresh token on 403 CSRF errors
        if (response.status === 403) {
            try {
                const body = await response.clone().json();
                if (body.detail && body.detail.includes('CSRF')) {
                    console.warn('[CSRF] Token rejected, refreshing...');
                    await refreshCSRFToken();
                }
            } catch (e) {
                // Not JSON, ignore
            }
        }

        // Extract new token from response headers
        const newToken = response.headers.get('X-CSRF-Token');
        if (newToken && newToken !== csrfToken) {
            csrfToken = newToken;
            console.log('[CSRF] Token updated from response');
        }

        return response;
    };

    // Fetch token on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fetchCSRFToken);
    } else {
        fetchCSRFToken();
    }

    // Expose helper functions globally
    window.csrf = {
        getToken: getCSRFToken,
        refreshToken: refreshCSRFToken
    };

    console.log('[CSRF] Helper loaded - fetch() calls will auto-inject tokens');
})();
