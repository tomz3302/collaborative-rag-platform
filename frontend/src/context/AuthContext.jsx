import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext();

// Get base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Token expires after 4 hours (in milliseconds)
const TOKEN_EXPIRY_MS = 4 * 60 * 60 * 1000;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Logout function
  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('tokenExpiry');
    localStorage.removeItem('user');
    localStorage.removeItem('activeSpaceId');
  }, []);

  // Check token expiry
  const isTokenExpired = useCallback(() => {
    const expiry = localStorage.getItem('tokenExpiry');
    if (!expiry) return true;
    return Date.now() > parseInt(expiry, 10);
  }, []);

  // Auto-load user from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');

    if (storedToken && storedUser && !isTokenExpired()) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    } else if (storedToken) {
      // Token expired, clean up
      logout();
    }
    setIsLoading(false);
  }, [isTokenExpired, logout]);

  // Set up auto-logout timer
  useEffect(() => {
    if (!token) return;

    const expiry = localStorage.getItem('tokenExpiry');
    if (!expiry) return;

    const timeUntilExpiry = parseInt(expiry, 10) - Date.now();
    if (timeUntilExpiry <= 0) {
      logout();
      return;
    }

    const timer = setTimeout(() => {
      logout();
      window.location.href = '/login';
    }, timeUntilExpiry);

    return () => clearTimeout(timer);
  }, [token, logout]);

  // Login function
  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/jwt/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'LOGIN_BAD_CREDENTIALS');
    }

    const data = await response.json();
    const accessToken = data.access_token;

    // Store token with expiry
    const expiryTime = Date.now() + TOKEN_EXPIRY_MS;
    localStorage.setItem('token', accessToken);
    localStorage.setItem('tokenExpiry', expiryTime.toString());

    // Fetch user info
    const userResponse = await fetch(`${API_BASE_URL}/users/me`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });

    if (!userResponse.ok) {
      throw new Error('Failed to fetch user info');
    }

    const userData = await userResponse.json();
    localStorage.setItem('user', JSON.stringify(userData));
    
    // Clear any previously selected space
    localStorage.removeItem('activeSpaceId');

    setToken(accessToken);
    setUser(userData);

    return userData;
  };

  // Register function
  const register = async (email, password, fullName) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        is_active: true,
        is_superuser: false,
        is_verified: false,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    return await response.json();
  };

  // Verify email function
  const verifyEmail = async (verificationToken) => {
    const response = await fetch(`${API_BASE_URL}/auth/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: verificationToken }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'VERIFY_USER_BAD_TOKEN');
    }

    return await response.json();
  };

  // Get auth header for API calls
  const getAuthHeader = useCallback(() => {
    if (!token || isTokenExpired()) {
      logout();
      return {};
    }
    return { 'Authorization': `Bearer ${token}` };
  }, [token, isTokenExpired, logout]);

  return (
    <AuthContext.Provider value={{ 
      user, 
      token,
      isLoading,
      login, 
      logout, 
      register,
      verifyEmail,
      getAuthHeader,
      isAuthenticated: !!token && !isTokenExpired()
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);