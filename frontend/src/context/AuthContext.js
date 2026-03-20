import React, { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize user on mount
  useEffect(() => {
    try {
      const token = localStorage.getItem('token');
      const userData = localStorage.getItem('user');
      
      console.log('[AUTH] Initializing. Token exists:', !!token);
      
      if (token && userData) {
        try {
          const parsedUser = JSON.parse(userData);
          setUser(parsedUser);
          console.log('[AUTH] User restored from localStorage:', parsedUser.email);
        } catch (parseError) {
          console.error('[AUTH] Error parsing user data:', parseError);
          // Clear invalid data
          localStorage.removeItem('user');
          localStorage.removeItem('token');
        }
      }
    } catch (err) {
      console.error('[AUTH] Error during initialization:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    try {
      console.log('[AUTH] Login attempt:', email);
      setError(null);
      
      if (!email || !password) {
        throw new Error('Email and password are required');
      }

      const response = await fetch('http://localhost:8000/api/v1/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      console.log('[AUTH] Login response status:', response.status);

      if (!response.ok) {
        throw new Error(`Login failed: ${response.status}`);
      }

      const data = await response.json();
      console.log('[AUTH] Login response:', data);

      if (data.token && data.user) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        setUser(data.user);
        console.log('[AUTH] Login successful');
        return true;
      } else {
        throw new Error(data.detail || 'No token in response');
      }
    } catch (error) {
      console.error('[AUTH] Login error:', error);
      setError(error.message);
      return false;
    }
  };

  const logout = () => {
    try {
      console.log('[AUTH] Logout');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setUser(null);
      setError(null);
    } catch (error) {
      console.error('[AUTH] Logout error:', error);
    }
  };

  const value = {
    user,
    login,
    logout,
    loading,
    error
  };

  console.log('[AUTH] Provider state:', { user: user?.email, loading, error });

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};