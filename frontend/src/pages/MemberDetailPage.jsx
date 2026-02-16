import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { membersAPI } from '../api/members';
import { useAuth } from '../hooks/useAuth';
import Header from '../components/layout/Header';
import Button from '../components/common/Button';
import Select from '../components/common/Select';
import Modal from '../components/common/Modal';
import FECContributions from '../components/members/FECContributions';

const statusLabels = {
  PENDING: 'Pending Review',
  ASSIGNED: 'Under Review',
  VETTED: 'Approved',
  REJECTED: 'Rejected',
};

const statusColors = {
  PENDING: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  ASSIGNED: 'bg-blue-100 text-blue-800 border-blue-300',
  VETTED: 'bg-green-100 text-green-800 border-green-300',
  REJECTED: 'bg-red-100 text-red-800 border-red-300',
};

const MemberDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAdmin } = useAuth();
  const backPath = location.state?.from || '/admin';
  const searchQuery = location.state?.searchQuery;
  const resultIds = location.state?.resultIds;
  const currentIndex = location.state?.currentIndex;
  const tab = location.state?.tab;
  const hasSearchContext = resultIds && resultIds.length > 0;
  const prevId = hasSearchContext && currentIndex > 0 ? resultIds[currentIndex - 1] : null;
  const nextId = hasSearchContext && currentIndex < resultIds.length - 1 ? resultIds[currentIndex + 1] : null;
  const [member, setMember] = useState(null);
  const [formConfig, setFormConfig] = useState(null);
  const [tagConfig, setTagConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newNote, setNewNote] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [showDeleteSection, setShowDeleteSection] = useState(false);

  useEffect(() => {
    loadMember();
    loadFormConfig();
    loadTagConfig();
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

  const loadTagConfig = async () => {
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}api/public/tag-config`);
      const config = await response.json();
      setTagConfig(config);
    } catch (err) {
      console.error('Failed to load tag config:', err);
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
        navigate(backPath, { state: { tab, searchQuery } });
      } else {
        loadMember();
      }
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleProcessingToggle = async () => {
    try {
      const data = await membersAPI.updateProcessing(id, !member.processing_completed);
      setMember(data);
    } catch (err) {
      console.error('Failed to update processing status:', err);
    }
  };

  const handleTagChange = async (categoryKey, value) => {
    const currentTags = member.tags || {};
    const updatedTags = { ...currentTags, [categoryKey]: value };
    try {
      const data = await membersAPI.updateTags(id, updatedTags);
      setMember(data);
    } catch (err) {
      console.error('Failed to update tags:', err);
    }
  };

  const handleMultiTagToggle = async (categoryKey, option) => {
    const currentTags = member.tags || {};
    const currentValues = currentTags[categoryKey] || [];
    const updatedValues = currentValues.includes(option)
      ? currentValues.filter(v => v !== option)
      : [...currentValues, option];
    const updatedTags = { ...currentTags, [categoryKey]: updatedValues };
    try {
      const data = await membersAPI.updateTags(id, updatedTags);
      setMember(data);
    } catch (err) {
      console.error('Failed to update tags:', err);
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

  const buildGoogleSearchUrl = (query) => {
    return `https://www.google.com/search?q=${encodeURIComponent(query)}`;
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
            <Button className="mt-4" onClick={() => navigate(backPath, { state: { tab, searchQuery } })}>
              Go Back
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const fullName = `${member.first_name} ${member.last_name}`;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-4xl mx-auto px-4 py-8">
        <Button variant="ghost" onClick={() => navigate(backPath, { state: { tab, searchQuery } })} className="mb-4">
          &larr; Back
        </Button>

        {hasSearchContext && (
          <div className="flex items-center justify-between bg-white shadow rounded-lg px-4 py-3 mb-4">
            <button
              onClick={() => prevId && navigate(`/members/${prevId}`, {
                state: { from: backPath, tab, searchQuery, resultIds, currentIndex: currentIndex - 1 }
              })}
              disabled={!prevId}
              className={`text-sm font-medium px-3 py-1 rounded ${prevId ? 'text-primary-600 hover:bg-primary-50' : 'text-gray-300 cursor-not-allowed'}`}
            >
              &larr; Prev
            </button>
            <span className="text-sm text-gray-600">
              Result {currentIndex + 1} of {resultIds.length} for &ldquo;{searchQuery}&rdquo;
            </span>
            <button
              onClick={() => nextId && navigate(`/members/${nextId}`, {
                state: { from: backPath, tab, searchQuery, resultIds, currentIndex: currentIndex + 1 }
              })}
              disabled={!nextId}
              className={`text-sm font-medium px-3 py-1 rounded ${nextId ? 'text-primary-600 hover:bg-primary-50' : 'text-gray-300 cursor-not-allowed'}`}
            >
              Next &rarr;
            </button>
          </div>
        )}

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          {/* Header with name and status */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {fullName}
              </h1>
              <p className="text-gray-600">Application ID: {member.id}</p>
            </div>
            <div className="text-right">
              <span className={`inline-block px-3 py-1 text-sm font-medium rounded-full border ${statusColors[member.status]}`}>
                {statusLabels[member.status] || member.status}
              </span>
              {member.processing_completed && (
                <span className="inline-block ml-2 px-3 py-1 text-sm font-medium rounded-full bg-purple-100 text-purple-800 border border-purple-300">
                  Processing Complete
                </span>
              )}
            </div>
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

          {/* Google Search Links */}
          <div className="mb-6 border-t pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Google Search</h2>
            <div className="flex flex-wrap gap-3">
              {member.phone_number && (
                <a
                  href={buildGoogleSearchUrl(`${fullName} ${member.phone_number}`)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2.5 bg-white border-2 border-blue-300 text-blue-700 text-sm font-semibold rounded-lg shadow-sm hover:bg-blue-50 hover:border-blue-400 hover:shadow transition-all"
                >
                  <svg className="mr-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                  Name + Phone
                  <svg className="ml-2 w-3.5 h-3.5 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              )}
              {member.email && (
                <a
                  href={buildGoogleSearchUrl(`${fullName} ${member.email}`)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2.5 bg-white border-2 border-blue-300 text-blue-700 text-sm font-semibold rounded-lg shadow-sm hover:bg-blue-50 hover:border-blue-400 hover:shadow transition-all"
                >
                  <svg className="mr-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                  Name + Email
                  <svg className="ml-2 w-3.5 h-3.5 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              )}
              {member.city && (
                <a
                  href={buildGoogleSearchUrl(`${fullName} ${member.city}`)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2.5 bg-white border-2 border-blue-300 text-blue-700 text-sm font-semibold rounded-lg shadow-sm hover:bg-blue-50 hover:border-blue-400 hover:shadow transition-all"
                >
                  <svg className="mr-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                  Name + City
                  <svg className="ml-2 w-3.5 h-3.5 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              )}
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

          {/* Tags */}
          {tagConfig && (
            <div className="mb-6 border-t pt-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Tags</h2>
              <div className="space-y-4">
                {tagConfig.categories.map((category) => {
                  const currentValue = member.tags?.[category.key];

                  if (category.multiple) {
                    const selectedValues = Array.isArray(currentValue) ? currentValue : [];
                    return (
                      <div key={category.key}>
                        <p className="text-sm font-medium text-gray-700 mb-2">{category.label}</p>
                        <div className="flex flex-wrap gap-2">
                          {category.options.map((option) => {
                            const isSelected = selectedValues.includes(option);
                            return (
                              <button
                                key={option}
                                onClick={() => handleMultiTagToggle(category.key, option)}
                                className={`px-3 py-1.5 text-sm rounded-full border-2 font-medium transition-all cursor-pointer ${
                                  isSelected
                                    ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                                    : 'bg-white text-gray-600 border-gray-300 hover:border-primary-400 hover:text-primary-700 hover:shadow-sm'
                                }`}
                              >
                                {isSelected && <span className="mr-1">&#10003;</span>}
                                {option}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div key={category.key}>
                      <p className="text-sm font-medium text-gray-700 mb-2">{category.label}</p>
                      <div className="flex flex-wrap gap-2">
                        {category.options.map((option) => {
                          const isSelected = currentValue === option;
                          return (
                            <button
                              key={option}
                              onClick={() => handleTagChange(category.key, isSelected ? null : option)}
                              className={`px-3 py-1.5 text-sm rounded-full border-2 font-medium transition-all cursor-pointer ${
                                isSelected
                                  ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                                  : 'bg-white text-gray-600 border-gray-300 hover:border-primary-400 hover:text-primary-700 hover:shadow-sm'
                              }`}
                            >
                              {isSelected && <span className="mr-1">&#10003;</span>}
                              {option}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Vetting Status */}
          <div className="mb-6 border-t pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Vetting</h2>
            <div className="flex items-center gap-4 mb-4">
              <span className="text-sm text-gray-600">Current status:</span>
              <span className={`inline-block px-3 py-1 text-sm font-medium rounded-full border ${statusColors[member.status]}`}>
                {statusLabels[member.status] || member.status}
              </span>
            </div>
            <div className="flex gap-2">
              {member.status !== 'VETTED' && (
                <Button onClick={() => handleStatusChange('VETTED')}>
                  Accept
                </Button>
              )}
              {member.status !== 'REJECTED' && (
                <Button variant="danger" onClick={() => handleStatusChange('REJECTED')}>
                  Reject
                </Button>
              )}
            </div>
          </div>

          {/* Processing Completed */}
          <div className="mb-6 border-t pt-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Processing</h2>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={member.processing_completed || false}
                onChange={handleProcessingToggle}
                className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">
                All processing has been completed for this member
              </span>
            </label>
          </div>

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
        <div className="bg-white shadow rounded-lg p-6 mb-6">
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

        {/* Delete Member (Admin Only) — at the very bottom, collapsed by default */}
        {isAdmin && (
          <div className="bg-white shadow rounded-lg p-6">
            {!showDeleteSection ? (
              <button
                onClick={() => setShowDeleteSection(true)}
                className="text-sm text-gray-400 hover:text-red-600 transition-colors"
              >
                Show danger zone...
              </button>
            ) : (
              <div>
                <h2 className="text-lg font-semibold text-red-700 mb-2">Danger Zone</h2>
                <p className="text-sm text-gray-600 mb-4">
                  Permanently delete this member and all associated data. This action cannot be undone.
                </p>
                <Button variant="danger" onClick={handleDeleteClick}>
                  Delete Member
                </Button>
              </div>
            )}
          </div>
        )}
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
              onClick={handleDeleteCancel}
              variant="secondary"
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteConfirm}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default MemberDetailPage;
