import React, { createContext, useState, useEffect } from 'react';
import { authAPI } from '../api/auth';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');

    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const data = await authAPI.login(username, password);

    localStorage.setItem('access_token', data.access_token);
    const userData = {
      id: data.user_id,
      username: data.username,
      role: data.role,
      full_name: data.full_name,
    };
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);

    return userData;
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
  };

  const isAdmin = () => {
    return user?.role === 'SUPER_ADMIN';
  };

  const isVetter = () => {
    return user?.role === 'VETTER';
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        isAdmin,
        isVetter,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
