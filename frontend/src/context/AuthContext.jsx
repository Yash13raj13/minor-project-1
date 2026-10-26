import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState({
    id: 3,
    full_name: 'Priya Sharma (Citizen)',
    email: 'citizen@civiclens.gov',
    role: 'CITIZEN',
  });
  const [token, setToken] = useState(localStorage.getItem('civiclens_token') || 'demo-token');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchUser = async () => {
      const storedToken = localStorage.getItem('civiclens_token');
      if (storedToken && !storedToken.startsWith('mock-')) {
        try {
          const userData = await authAPI.getCurrentUser();
          if (userData) setUser(userData);
        } catch (err) {
          console.warn("Using offline user session");
        }
      }
    };
    fetchUser();
  }, []);

  const login = async (email, password) => {
    try {
      const data = await authAPI.login(email, password);
      localStorage.setItem('civiclens_token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      return { success: true, user: data.user };
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || 'Login failed.',
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('civiclens_token');
    setToken(null);
    setUser(null);
  };

  const switchDemoRole = async (role) => {
    if (role === 'CITIZEN') {
      const res = await login('citizen@civiclens.gov', 'Citizen@123');
      if (!res.success) {
        setUser({ id: 3, full_name: 'Priya Sharma (Citizen)', email: 'citizen@civiclens.gov', role: 'CITIZEN' });
      }
    } else if (role === 'OFFICER') {
      const res = await login('officer@civiclens.gov', 'Officer@123');
      if (!res.success) {
        setUser({ id: 2, full_name: 'Rajesh Verma (Zonal Officer)', email: 'officer@civiclens.gov', role: 'OFFICER', department_id: 2 });
      }
    } else if (role === 'ADMIN') {
      const res = await login('admin@civiclens.gov', 'Admin@123');
      if (!res.success) {
        setUser({ id: 1, full_name: 'Municipal Commissioner (Admin)', email: 'admin@civiclens.gov', role: 'ADMIN' });
      }
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, switchDemoRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
