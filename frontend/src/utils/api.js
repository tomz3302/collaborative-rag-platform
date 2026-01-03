/**
 * API Helper - Centralized fetch wrapper with auth headers
 * Automatically attaches Bearer token to all requests
 */

// Get auth token from localStorage
const getAuthToken = () => localStorage.getItem('token');

// Check if token is expired
const isTokenExpired = () => {
  const expiry = localStorage.getItem('tokenExpiry');
  if (!expiry) return true;
  return Date.now() > parseInt(expiry, 10);
};

// Handle auth errors (401) by redirecting to login
const handleAuthError = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('tokenExpiry');
  localStorage.removeItem('user');
  localStorage.removeItem('activeSpaceId');
  window.location.href = '/login';
};

/**
 * Authenticated fetch wrapper
 * @param {string} url - The URL to fetch (Vite proxy handles routing)
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<Response>}
 */
export const apiFetch = async (url, options = {}) => {
  const token = getAuthToken();
  
  // Check if token expired before making request
  if (token && isTokenExpired()) {
    handleAuthError();
    throw new Error('Session expired');
  }
  
  // Build headers with auth token
  const headers = {
    ...options.headers,
  };
  
  // Add auth header if token exists (for protected routes)
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // Add Content-Type for JSON requests (but not for FormData)
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    handleAuthError();
    throw new Error('Unauthorized');
  }
  
  return response;
};

/**
 * Shorthand for GET requests
 */
export const apiGet = (url) => apiFetch(url);

/**
 * Shorthand for POST requests with JSON body
 */
export const apiPost = (url, data) => 
  apiFetch(url, {
    method: 'POST',
    body: data instanceof FormData ? data : JSON.stringify(data),
  });

/**
 * Shorthand for PUT requests
 */
export const apiPut = (url, data) => 
  apiFetch(url, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

/**
 * Shorthand for DELETE requests
 */
export const apiDelete = (url) => 
  apiFetch(url, { method: 'DELETE' });

export default apiFetch;
