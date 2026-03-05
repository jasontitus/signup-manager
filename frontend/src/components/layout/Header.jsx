import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Button from '../common/Button';

const Header = ({ tabs, activeTab, onTabChange, rightContent }) => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6 py-0">
          <h1 className="text-lg font-bold text-primary-600 shrink-0 py-2">
            <button
              onClick={() => navigate('/staff')}
              className="hover:text-primary-700 transition-colors cursor-pointer"
            >
              Membership Portal
            </button>
          </h1>
          {tabs && (
            <nav className="flex space-x-6">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => onTabChange(tab.key)}
                  className={`${
                    activeTab === tab.key
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  } whitespace-nowrap py-2.5 border-b-2 font-medium text-sm`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          )}
          <div className="flex-1" />
          {rightContent}
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-xs text-gray-500">
                {user.full_name}
              </span>
            )}
            {user && (
              <button
                onClick={handleLogout}
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                Logout
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
