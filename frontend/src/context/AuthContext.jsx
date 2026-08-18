import React, { createContext, useState, useEffect, useContext } from 'react';
import client from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load user from localStorage token payload on mount
  useEffect(() => {
    const loadUser = async () => {
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        try {
          const response = await client.get('auth/profile/');
          if (response.data && response.data.success) {
            setUser(response.data.data);
          }
        } catch (error) {
          console.error('Failed to load user profile on mount:', error);
          logout();
        }
      }
      setLoading(false);
    };

    loadUser();

    // Listen to global logout event from axios client
    const handleGlobalLogout = () => {
      setUser(null);
    };
    window.addEventListener('auth-logout', handleGlobalLogout);

    return () => {
      window.removeEventListener('auth-logout', handleGlobalLogout);
    };
  }, []);

  const login = async (username, password) => {
    try {
      const response = await client.post('auth/login/', { username, password });
      const { access, refresh, user: userData } = response.data.data;
      
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      setUser(userData);
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      const message = error.response?.data?.message || error.response?.data?.detail || 'Login failed. Please check your credentials.';
      return { success: false, message };
    }
  };

  const register = async (userData) => {
    try {
      const response = await client.post('auth/register/', userData);
      if (response.data && response.data.success) {
        return { success: true, message: response.data.message };
      }
      return { success: false, message: 'Registration failed.' };
    } catch (error) {
      console.error('Registration error:', error);
      const message = error.response?.data?.error?.message || 'Registration failed. Please check input parameters.';
      return { success: false, message };
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
