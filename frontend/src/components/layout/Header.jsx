import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Button from '../common/Button';

const Header = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div>
            <h1 className="text-2xl font-bold text-primary-600">
              <button
                onClick={() => navigate('/staff')}
                className="hover:text-primary-700 transition-colors cursor-pointer"
              >
                Membership Portal
              </button>
            </h1>
            {user && (
              <p className="text-sm text-gray-600">
                Logged in as: {user.full_name} ({isAdmin() ? 'Admin' : 'Vetter'})
              </p>
            )}
          </div>
          {user && (
            <Button variant="secondary" onClick={handleLogout}>
              Logout
            </Button>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
