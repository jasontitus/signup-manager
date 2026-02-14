import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/layout/ProtectedRoute';
import PublicApplicationForm from './pages/PublicApplicationForm';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import VetterDashboard from './pages/VetterDashboard';
import MemberDetailPage from './pages/MemberDetailPage';
import { useAuth } from './hooks/useAuth';

const StaffRedirect = () => {
  const { user, isAdmin } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (isAdmin()) {
    return <Navigate to="/admin" replace />;
  }

  return <Navigate to="/vetter" replace />;
};

function App() {
  return (
    <Router basename={import.meta.env.BASE_URL.replace(/\/+$/, '')}>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<PublicApplicationForm />} />
          <Route path="/login" element={<Login />} />

          {/* Protected Routes */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute requireAdmin={true}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/vetter"
            element={
              <ProtectedRoute>
                <VetterDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/members/:id"
            element={
              <ProtectedRoute>
                <MemberDetailPage />
              </ProtectedRoute>
            }
          />

          {/* Staff redirect route */}
          <Route path="/staff" element={<StaffRedirect />} />

          {/* 404 - redirect to home (signup form) */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
