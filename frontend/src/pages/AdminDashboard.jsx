import React, { useState, useEffect, useContext } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { membersAPI } from '../api/members';
import { usersAPI } from '../api/users';
import { AuthContext } from '../context/AuthContext';
import Header from '../components/layout/Header';
import MemberCard from '../components/members/MemberCard';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Modal from '../components/common/Modal';

const AdminDashboard = () => {
  const { user: currentUser } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(location.state?.tab || 'triage');
  const [members, setMembers] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState(location.state?.searchQuery || '');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [userFormOpen, setUserFormOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [reclaimingStale, setReclaimingStale] = useState(false);
  const [reclaimMessage, setReclaimMessage] = useState('');
  const [tagConfig, setTagConfig] = useState(null);
  const [tagFilters, setTagFilters] = useState({});
  const [statusFilter, setStatusFilter] = useState(null);
  const [processingFilter, setProcessingFilter] = useState(false);
  const [contactListMode, setContactListMode] = useState(false);
  const [contacts, setContacts] = useState([]);
  const [loadingContacts, setLoadingContacts] = useState(false);
  const [copiedEmails, setCopiedEmails] = useState(false);
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    role: 'VETTER',
    full_name: '',
  });

  useEffect(() => {
    loadMembers();
    loadUsers();
    loadTagConfig();
    if (location.state?.searchQuery) {
      handleSearch(location.state.searchQuery);
    }
  }, []);

  useEffect(() => {
    if (contactListMode) {
      loadContacts();
    }
  }, [statusFilter]);

  const loadTagConfig = async () => {
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}api/public/tag-config`);
      const config = await response.json();
      setTagConfig(config);
    } catch (err) {
      console.error('Failed to load tag config:', err);
    }
  };

  const handleTagFilterToggle = (categoryKey, option) => {
    setTagFilters((prev) => {
      const current = prev[categoryKey] || [];
      const updated = current.includes(option)
        ? current.filter((v) => v !== option)
        : [...current, option];
      if (updated.length === 0) {
        const { [categoryKey]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [categoryKey]: updated };
    });
  };

  const clearTagFilters = () => setTagFilters({});

  const hasActiveTagFilters = Object.keys(tagFilters).length > 0;

  const filterByTags = (memberList) => {
    if (!hasActiveTagFilters) return memberList;
    return memberList.filter((m) => {
      const memberTags = m.tags || {};
      return Object.entries(tagFilters).every(([catKey, filterValues]) => {
        const tagValue = memberTags[catKey];
        if (Array.isArray(tagValue)) {
          return filterValues.some((fv) => tagValue.includes(fv));
        }
        return filterValues.includes(tagValue);
      });
    });
  };

  const loadMembers = async () => {
    setLoading(true);
    try {
      const data = await membersAPI.list();
      setMembers(data);
    } catch (err) {
      console.error('Failed to load members:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const data = await usersAPI.list();
      setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await usersAPI.create(newUser);
      setUserFormOpen(false);
      setNewUser({ username: '', password: '', role: 'VETTER', full_name: '' });
      loadUsers();
    } catch (err) {
      console.error('Failed to create user:', err);
    }
  };

  const handleDeleteClick = (user) => {
    setUserToDelete(user);
    setDeleteError('');
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!userToDelete) return;

    try {
      await usersAPI.delete(userToDelete.id);
      setDeleteConfirmOpen(false);
      setUserToDelete(null);
      loadUsers();
    } catch (err) {
      console.error('Failed to delete user:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to delete user. Please try again.';
      setDeleteError(errorMessage);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false);
    setUserToDelete(null);
    setDeleteError('');
  };

  const handleReclaimStale = async () => {
    setReclaimingStale(true);
    setReclaimMessage('');
    try {
      const result = await membersAPI.reclaimStaleAssignments();
      setReclaimMessage(result.message);
      if (result.reclaimed_count > 0) {
        loadMembers(); // Reload to show updated statuses
      }
    } catch (err) {
      console.error('Failed to reclaim stale assignments:', err);
      setReclaimMessage('Error reclaiming stale assignments');
    } finally {
      setReclaimingStale(false);
    }
  };

  const handleSearch = async (query) => {
    if (!query || query.trim().length === 0) {
      setSearchResults([]);
      setSearchQuery('');
      return;
    }

    setSearching(true);
    try {
      const results = await membersAPI.search(query);
      setSearchResults(results);
      setSearchQuery(query);
    } catch (err) {
      console.error('Failed to search members:', err);
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
  };

  const loadContacts = async () => {
    setLoadingContacts(true);
    try {
      const params = {};
      if (statusFilter) params.status_filter = statusFilter;
      const data = await membersAPI.getContacts(params);
      setContacts(data);
    } catch (err) {
      console.error('Failed to load contacts:', err);
    } finally {
      setLoadingContacts(false);
    }
  };

  const toggleContactListMode = () => {
    if (!contactListMode) {
      loadContacts();
    }
    setContactListMode(!contactListMode);
  };

  const handleCopyEmails = () => {
    const filteredContacts = applyContactFilters(contacts);
    const emails = filteredContacts.map((c) => c.email).filter(Boolean).join(', ');
    navigator.clipboard.writeText(emails).then(() => {
      setCopiedEmails(true);
      setTimeout(() => setCopiedEmails(false), 2000);
    });
  };

  const applyContactFilters = (contactList) => {
    let filtered = contactList;
    if (processingFilter) {
      // contacts endpoint doesn't have processing_completed, so we filter from local members
      const notProcessedIds = new Set(members.filter((m) => !m.processing_completed).map((m) => m.id));
      filtered = filtered.filter((c) => notProcessedIds.has(c.id));
    }
    filtered = filterByTags(filtered);
    return filtered;
  };

  const pendingMembers = members.filter((m) => m.status === 'PENDING');
  const assignedMembers = members.filter((m) => m.status === 'ASSIGNED');
  const vettedMembers = members.filter((m) => m.status === 'VETTED');
  const unsureMembers = members.filter((m) => m.status === 'UNSURE');
  const rejectedMembers = members.filter((m) => m.status === 'REJECTED');
  const notProcessedMembers = members.filter((m) => !m.processing_completed);
  const vetters = users.filter((u) => u.role === 'VETTER' && u.is_active);

  const applyAllFilters = (memberList) => {
    let filtered = memberList;
    if (statusFilter) {
      filtered = filtered.filter((m) => m.status === statusFilter);
    }
    if (processingFilter) {
      filtered = filtered.filter((m) => !m.processing_completed);
    }
    filtered = filterByTags(filtered);
    return filtered;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {['triage', 'database', 'staff'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`${
                  activeTab === tab
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm capitalize`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        {/* Triage Tab */}
        {activeTab === 'triage' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Pending Applications ({pendingMembers.length})
            </h2>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-blue-800">
                Applications are automatically assigned to vetters when they log in. Vetters will receive the next pending application in the queue.
              </p>
            </div>
            {pendingMembers.length === 0 ? (
              <p className="text-gray-600">No pending applications</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {pendingMembers.map((member) => (
                  <MemberCard key={member.id} member={member} tab="triage" />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Database Tab */}
        {activeTab === 'database' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-900">All Members</h2>
              <div className="flex gap-2">
                <Button
                  onClick={toggleContactListMode}
                  variant={contactListMode ? 'primary' : 'secondary'}
                >
                  {contactListMode ? 'Card View' : 'Contact List'}
                </Button>
                <Button
                  onClick={handleReclaimStale}
                  disabled={reclaimingStale}
                  variant="secondary"
                >
                  {reclaimingStale ? 'Checking...' : 'Reclaim Stale Assignments'}
                </Button>
              </div>
            </div>

            {reclaimMessage && (
              <div className={`mb-4 p-3 rounded ${
                reclaimMessage.includes('Error') ? 'bg-red-100 text-red-700' :
                reclaimMessage.includes('0') ? 'bg-blue-100 text-blue-700' :
                'bg-green-100 text-green-700'
              }`}>
                {reclaimMessage}
              </div>
            )}

            {/* Search Input */}
            <div className="mb-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Search by name, address, location, notes, or custom fields..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    if (e.target.value.length >= 2) {
                      handleSearch(e.target.value);
                    } else if (e.target.value.length === 0) {
                      clearSearch();
                    }
                  }}
                  className="flex-1"
                />
                {searchQuery && (
                  <Button onClick={clearSearch} variant="secondary">
                    Clear
                  </Button>
                )}
              </div>
              {searching && (
                <p className="text-sm text-gray-600 mt-2">Searching...</p>
              )}
              {searchQuery && !searching && (
                <p className="text-sm text-gray-600 mt-2">
                  Found {applyAllFilters(searchResults).length} result{applyAllFilters(searchResults).length !== 1 ? 's' : ''}
                  {(hasActiveTagFilters || statusFilter || processingFilter) && ` (${searchResults.length} before filters)`}
                </p>
              )}
            </div>

            {/* Tag Filters */}
            {tagConfig && (
              <div className="mb-4 bg-white rounded-lg shadow px-4 py-3">
                <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
                  <h3 className="text-sm font-semibold text-gray-700 mr-1">Filter by Tags</h3>
                  {tagConfig.categories.map((category) => (
                    <div key={category.key} className="flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-medium text-gray-700">{category.label}:</span>
                      {category.options.map((option) => {
                        const isActive = (tagFilters[category.key] || []).includes(option);
                        return (
                          <button
                            key={option}
                            onClick={() => handleTagFilterToggle(category.key, option)}
                            className={`px-3 py-1.5 text-sm rounded-full border-2 font-medium transition-all cursor-pointer ${
                              isActive
                                ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                                : 'bg-white text-gray-600 border-gray-300 hover:border-primary-400 hover:text-primary-700 hover:shadow-sm'
                            }`}
                          >
                            {option}
                          </button>
                        );
                      })}
                    </div>
                  ))}
                  {hasActiveTagFilters && (
                    <button
                      onClick={clearTagFilters}
                      className="text-xs text-primary-600 hover:text-primary-800 font-medium"
                    >
                      Clear filters
                    </button>
                  )}
                </div>
              </div>
            )}

            {!searchQuery && (
              <div className="mb-4 flex flex-wrap gap-3">
                {[
                  { key: 'PENDING', label: 'Pending', count: pendingMembers.length, color: 'text-yellow-600', ring: 'ring-yellow-400' },
                  { key: 'ASSIGNED', label: 'Assigned', count: assignedMembers.length, color: 'text-blue-600', ring: 'ring-blue-400' },
                  { key: 'VETTED', label: 'Vetted', count: vettedMembers.length, color: 'text-green-600', ring: 'ring-green-400' },
                  { key: 'UNSURE', label: 'Unsure', count: unsureMembers.length, color: 'text-orange-600', ring: 'ring-orange-400' },
                  { key: 'REJECTED', label: 'Rejected', count: rejectedMembers.length, color: 'text-red-600', ring: 'ring-red-400' },
                ].map((stat) => (
                  <button
                    key={stat.key}
                    onClick={() => setStatusFilter(statusFilter === stat.key ? null : stat.key)}
                    className={`bg-white p-4 rounded-lg shadow flex-1 min-w-[100px] text-left cursor-pointer transition-all hover:shadow-md ${
                      statusFilter === stat.key ? `ring-2 ${stat.ring}` : ''
                    }`}
                  >
                    <p className="text-sm text-gray-600">{stat.label}</p>
                    <p className={`text-2xl font-bold ${stat.color}`}>{stat.count}</p>
                  </button>
                ))}
                <button
                  onClick={() => setProcessingFilter(!processingFilter)}
                  className={`bg-white p-4 rounded-lg shadow flex-1 min-w-[100px] text-left cursor-pointer transition-all hover:shadow-md ${
                    processingFilter ? 'ring-2 ring-purple-400' : ''
                  }`}
                >
                  <p className="text-sm text-gray-600">Not Processed</p>
                  <p className="text-2xl font-bold text-purple-600">{notProcessedMembers.length}</p>
                </button>
              </div>
            )}

            {contactListMode ? (
              <div>
                <div className="flex justify-between items-center mb-3">
                  <p className="text-sm text-gray-600">
                    {loadingContacts ? 'Loading contacts...' : `${applyContactFilters(contacts).length} contacts`}
                  </p>
                  <Button variant="secondary" onClick={handleCopyEmails} disabled={loadingContacts}>
                    {copiedEmails ? 'Copied!' : 'Copy Emails'}
                  </Button>
                </div>
                <div className="bg-white shadow rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Phone</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">City</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {applyContactFilters(contacts).map((contact) => {
                        const statusColorMap = {
                          PENDING: 'bg-yellow-100 text-yellow-800',
                          ASSIGNED: 'bg-blue-100 text-blue-800',
                          VETTED: 'bg-green-100 text-green-800',
                          UNSURE: 'bg-orange-100 text-orange-800',
                          REJECTED: 'bg-red-100 text-red-800',
                        };
                        return (
                          <tr
                            key={contact.id}
                            onClick={() => navigate(`/members/${contact.id}`, { state: { from: '/admin', tab: 'database' } })}
                            className="hover:bg-gray-50 cursor-pointer"
                          >
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">
                              {contact.first_name} {contact.last_name}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">{contact.email}</td>
                            <td className="px-4 py-3 text-sm text-gray-600">{contact.phone_number}</td>
                            <td className="px-4 py-3 text-sm text-gray-600">{contact.city}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColorMap[contact.status] || ''}`}>
                                {contact.status}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(() => {
                  const displayMembers = applyAllFilters(searchQuery ? searchResults : members);
                  return displayMembers.map((member, index) => (
                    <MemberCard
                      key={member.id}
                      member={member}
                      tab="database"
                      searchContext={searchQuery ? {
                        query: searchQuery,
                        resultIds: displayMembers.map(m => m.id),
                        currentIndex: index,
                      } : undefined}
                    />
                  ));
                })()}
              </div>
            )}
          </div>
        )}

        {/* Staff Tab */}
        {activeTab === 'staff' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-900">Staff Management</h2>
              <Button onClick={() => setUserFormOpen(true)}>Add User</Button>
            </div>
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Username
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Full Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {user.username}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.full_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.role}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            user.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.id !== currentUser?.id && (
                          <button
                            onClick={() => handleDeleteClick(user)}
                            className="text-red-600 hover:text-red-900"
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* User Form Modal */}
      <Modal
        isOpen={userFormOpen}
        onClose={() => setUserFormOpen(false)}
        title="Create New User"
      >
        <form onSubmit={handleCreateUser}>
          <Input
            label="Username"
            name="username"
            value={newUser.username}
            onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
            required
          />
          <Input
            label="Password"
            name="password"
            type="password"
            value={newUser.password}
            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            required
          />
          <Input
            label="Full Name"
            name="full_name"
            value={newUser.full_name}
            onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
            required
          />
          <Select
            label="Role"
            name="role"
            value={newUser.role}
            onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            options={[
              { value: 'VETTER', label: 'Vetter' },
              { value: 'SUPER_ADMIN', label: 'Super Admin' },
            ]}
          />
          <Button type="submit" className="w-full mt-4">
            Create User
          </Button>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteConfirmOpen}
        onClose={handleDeleteCancel}
        title="Confirm Delete User"
      >
        <div>
          <p className="text-gray-700 mb-4">
            Are you sure you want to delete user <strong>{userToDelete?.username}</strong>?
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

export default AdminDashboard;
