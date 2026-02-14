import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { membersAPI } from '../api/members';
import { useAuth } from '../hooks/useAuth';
import Header from '../components/layout/Header';
import Button from '../components/common/Button';
import Select from '../components/common/Select';
import Modal from '../components/common/Modal';
import FECContributions from '../components/members/FECContributions';

const MemberDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAdmin } = useAuth();
  const backPath = location.state?.from || '/admin';
  const [member, setMember] = useState(null);
  const [formConfig, setFormConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newNote, setNewNote] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  useEffect(() => {
    loadMember();
    loadFormConfig();
  }, [id]);

  const loadFormConfig = async () => {
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}api/public/form-config`);
      const config = await response.json();
      setFormConfig(config);
    } catch (err) {
      console.error('Failed to load form config:', err);
    }
  };

  const loadMember = async () => {
    setLoading(true);
    try {
      const data = await membersAPI.get(id);
      setMember(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load member');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      await membersAPI.updateStatus(id, newStatus);

      // If vetter completed vetting (VETTED or REJECTED), redirect to dashboard
      // They will see their next auto-assigned candidate there
      if (newStatus === 'VETTED' || newStatus === 'REJECTED') {
        navigate(backPath);
      } else {
        loadMember();
      }
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    setSavingNote(true);
    try {
      await membersAPI.addNote(id, newNote);
      setNewNote('');
      loadMember();
    } catch (err) {
      console.error('Failed to add note:', err);
    } finally {
      setSavingNote(false);
    }
  };

  const handleDeleteClick = () => {
    setDeleteError('');
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    try {
      await membersAPI.delete(id);
      navigate('/admin');
    } catch (err) {
      console.error('Failed to delete member:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to delete member. Please try again.';
      setDeleteError(errorMessage);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false);
    setDeleteError('');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-8">
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="bg-red-50 p-4 rounded-lg">
            <p className="text-red-800">{error}</p>
            <Button className="mt-4" onClick={() => navigate(backPath)}>
              Go Back
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const statusColors = {
    PENDING: 'bg-yellow-100 text-yellow-800',
    ASSIGNED: 'bg-blue-100 text-blue-800',
    VETTED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-4xl mx-auto px-4 py-8">
        <Button variant="ghost" onClick={() => navigate(backPath)} className="mb-4">
          ← Back
        </Button>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {member.first_name} {member.last_name}
              </h1>
              <p className="text-gray-600">Application ID: {member.id}</p>
            </div>
            <span className={`px-3 py-1 text-sm font-medium rounded-full ${statusColors[member.status]}`}>
              {member.status}
            </span>
          </div>

          {/* Contact Information */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Contact Information
            </h2>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-yellow-800">
                This information has been decrypted and logged in the audit trail.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Email</p>
                <p className="font-medium">{member.email}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Phone Number</p>
                <p className="font-medium">{member.phone_number}</p>
              </div>
              <div className="md:col-span-2">
                <p className="text-sm text-gray-600">Street Address</p>
                <p className="font-medium">{member.street_address}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">City</p>
                <p className="font-medium">{member.city}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Zip Code</p>
                <p className="font-medium">{member.zip_code}</p>
              </div>
            </div>
          </div>

          {/* Application Responses */}
          <div className="mb-6 border-t pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Application Responses</h2>
            {formConfig && member.custom_fields && Object.keys(member.custom_fields).length > 0 ? (
              formConfig.fields.map((fieldConfig) => {
                const value = member.custom_fields[fieldConfig.key];
                if (!value) return null;

                return (
                  <div key={fieldConfig.key} className="mb-4">
                    <p className="text-sm text-gray-600">{fieldConfig.label}</p>
                    <p className="font-medium whitespace-pre-wrap">{value}</p>
                  </div>
                );
              })
            ) : (
              <p className="text-gray-500 italic">No application responses provided</p>
            )}
          </div>

          {/* Campaign Contributions */}
          <FECContributions
            firstName={member.first_name}
            lastName={member.last_name}
            zipCode={member.zip_code}
          />

          {/* Status Update */}
          <div className="mb-6 border-t pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Update Status</h2>
            <div className="flex gap-2">
              {member.status !== 'VETTED' && (
                <Button onClick={() => handleStatusChange('VETTED')}>
                  Mark as Vetted
                </Button>
              )}
              {member.status !== 'REJECTED' && (
                <Button variant="danger" onClick={() => handleStatusChange('REJECTED')}>
                  Reject
                </Button>
              )}
            </div>
          </div>

          {/* Delete Member (Admin Only) */}
          {isAdmin && (
            <div className="mb-6 border-t pt-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Delete Member</h2>
              <p className="text-sm text-gray-600 mb-4">
                Permanently delete this member and all associated data. This action cannot be undone.
              </p>
              <Button variant="danger" onClick={handleDeleteClick}>
                Delete Member
              </Button>
            </div>
          )}

          {/* Internal Notes */}
          <div className="border-t pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Internal Notes</h2>

            {member.notes && (
              <div className="bg-gray-50 rounded-lg p-4 mb-4 max-h-64 overflow-y-auto">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">{member.notes}</pre>
              </div>
            )}

            <form onSubmit={handleAddNote}>
              <textarea
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Add an internal note..."
                rows="4"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <Button type="submit" disabled={savingNote || !newNote.trim()} className="mt-2">
                {savingNote ? 'Adding Note...' : 'Add Note'}
              </Button>
            </form>
          </div>
        </div>

        {/* Metadata */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Application Date</p>
              <p className="font-medium">{new Date(member.created_at).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-600">Last Updated</p>
              <p className="font-medium">{new Date(member.updated_at).toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteConfirmOpen}
        onClose={handleDeleteCancel}
        title="Confirm Delete Member"
      >
        <div>
          <p className="text-gray-700 mb-4">
            Are you sure you want to delete <strong>{member.first_name} {member.last_name}</strong>?
            This will permanently remove all data including encrypted PII and audit logs.
            This action cannot be undone.
          </p>
          {deleteError && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {deleteError}
            </div>
          )}
          <div className="flex gap-3">
            <Button
              onClick={handleDeleteConfirm}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              Delete
            </Button>
            <Button
              onClick={handleDeleteCancel}
              variant="secondary"
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default MemberDetailPage;
