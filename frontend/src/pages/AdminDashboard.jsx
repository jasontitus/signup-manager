import React, { useState, useEffect, useContext } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { membersAPI } from '../api/members';
import { usersAPI } from '../api/users';
import { tagsAPI } from '../api/tags';
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
  const [showArchived, setShowArchived] = useState(false);
  const [sortMode, setSortMode] = useState('recent');
  const [contactListMode, setContactListMode] = useState(false);
  const [contacts, setContacts] = useState([]);
  const [loadingContacts, setLoadingContacts] = useState(false);
  const [copiedEmails, setCopiedEmails] = useState(false);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedMemberIds, setSelectedMemberIds] = useState(new Set());
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const [pendingBulkAction, setPendingBulkAction] = useState(null);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [bulkTagCategory, setBulkTagCategory] = useState('');
  const [bulkTagValue, setBulkTagValue] = useState('');
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    role: 'VETTER',
    full_name: '',
  });

  // Tag management state
  const [tagCategories, setTagCategories] = useState([]);
  const [loadingTags, setLoadingTags] = useState(false);
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [tagForm, setTagForm] = useState({ key: '', label: '', options: [''], multiple: false });
  const [tagFormError, setTagFormError] = useState('');
  const [tagDeleteConfirmOpen, setTagDeleteConfirmOpen] = useState(false);
  const [categoryToDelete, setCategoryToDelete] = useState(null);
  const [deleteUsage, setDeleteUsage] = useState(null);
  const [loadingUsage, setLoadingUsage] = useState(false);

  useEffect(() => {
    loadMembers();
    loadUsers();
    loadTagConfig();
    if (activeTab === 'tags') loadTagCategories();
    if (location.state?.searchQuery) {
      handleSearch(location.state.searchQuery);
    }
  }, []);

  useEffect(() => {
    loadMembers();
  }, [showArchived]);

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
      const data = await membersAPI.list(null, showArchived);
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

  // Clear selection when filters change
  useEffect(() => {
    setSelectedMemberIds(new Set());
    setSelectMode(false);
  }, [statusFilter, showArchived, tagFilters, searchQuery, contactListMode]);

  const toggleMemberSelection = (memberId) => {
    setSelectedMemberIds((prev) => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      return next;
    });
  };

  const selectAllVisible = (visibleMembers) => {
    setSelectedMemberIds(new Set(visibleMembers.map((m) => m.id)));
  };

  const clearSelection = () => setSelectedMemberIds(new Set());

  const confirmBulkAction = (action) => {
    setPendingBulkAction(action);
    setBulkConfirmOpen(true);
  };

  const executeBulkAction = async () => {
    if (!pendingBulkAction) return;
    setBulkActionLoading(true);
    try {
      const ids = Array.from(selectedMemberIds);
      let updatedMembers;
      if (pendingBulkAction.type === 'status') {
        updatedMembers = await membersAPI.bulkUpdateStatus(ids, pendingBulkAction.value);
      } else if (pendingBulkAction.type === 'archive') {
        updatedMembers = await membersAPI.bulkUpdateArchived(ids, pendingBulkAction.value);
      } else if (pendingBulkAction.type === 'tag') {
        updatedMembers = await membersAPI.bulkUpdateTags(ids, pendingBulkAction.tagKey, pendingBulkAction.tagValue);
        setBulkTagCategory('');
        setBulkTagValue('');
      }
      // Merge updated members into local state
      setMembers((prev) => {
        const updatedMap = new Map(updatedMembers.map((m) => [m.id, m]));
        return prev.map((m) => updatedMap.get(m.id) || m);
      });
      setSelectedMemberIds(new Set());
      setSelectMode(false);
    } catch (err) {
      console.error('Bulk action failed:', err);
    } finally {
      setBulkActionLoading(false);
      setBulkConfirmOpen(false);
      setPendingBulkAction(null);
    }
  };

  // Tag management handlers
  const loadTagCategories = async () => {
    setLoadingTags(true);
    try {
      const config = await tagsAPI.getConfig();
      setTagCategories(config.categories || []);
    } catch (err) {
      console.error('Failed to load tag categories:', err);
    } finally {
      setLoadingTags(false);
    }
  };

  const openAddTagModal = () => {
    setEditingCategory(null);
    setTagForm({ key: '', label: '', options: [''], multiple: false });
    setTagFormError('');
    setTagModalOpen(true);
  };

  const openEditTagModal = (category) => {
    setEditingCategory(category);
    setTagForm({
      key: category.key,
      label: category.label,
      options: [...category.options],
      multiple: category.multiple,
    });
    setTagFormError('');
    setTagModalOpen(true);
  };

  const handleTagFormOptionChange = (index, value) => {
    setTagForm((prev) => {
      const options = [...prev.options];
      options[index] = value;
      return { ...prev, options };
    });
  };

  const addTagFormOption = () => {
    setTagForm((prev) => ({ ...prev, options: [...prev.options, ''] }));
  };

  const removeTagFormOption = (index) => {
    setTagForm((prev) => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index),
    }));
  };

  const handleTagFormSave = async () => {
    setTagFormError('');
    const trimmedOptions = tagForm.options.map((o) => o.trim()).filter(Boolean);
    if (!tagForm.label.trim()) {
      setTagFormError('Label is required');
      return;
    }
    if (trimmedOptions.length === 0) {
      setTagFormError('At least one option is required');
      return;
    }

    try {
      if (editingCategory) {
        await tagsAPI.updateCategory(editingCategory.key, {
          label: tagForm.label.trim(),
          options: trimmedOptions,
          multiple: tagForm.multiple,
        });
      } else {
        if (!tagForm.key.trim()) {
          setTagFormError('Key is required');
          return;
        }
        await tagsAPI.addCategory({
          key: tagForm.key.trim(),
          label: tagForm.label.trim(),
          options: trimmedOptions,
          multiple: tagForm.multiple,
        });
      }
      setTagModalOpen(false);
      loadTagCategories();
      loadTagConfig(); // refresh filters too
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setTagFormError(detail.map((d) => d.msg).join(', '));
      } else {
        setTagFormError(detail || 'Failed to save category');
      }
    }
  };

  const openDeleteTagConfirm = async (category) => {
    setCategoryToDelete(category);
    setDeleteUsage(null);
    setLoadingUsage(true);
    setTagDeleteConfirmOpen(true);
    try {
      const usage = await tagsAPI.getOptionUsage(category.key);
      setDeleteUsage(usage);
    } catch (err) {
      console.error('Failed to load usage:', err);
    } finally {
      setLoadingUsage(false);
    }
  };

  const handleDeleteTagConfirm = async () => {
    if (!categoryToDelete) return;
    try {
      await tagsAPI.deleteCategory(categoryToDelete.key);
      setTagDeleteConfirmOpen(false);
      setCategoryToDelete(null);
      loadTagCategories();
      loadTagConfig();
    } catch (err) {
      console.error('Failed to delete category:', err);
    }
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
    filtered = filterByTags(filtered);
    return sortMembers(filtered);
  };

  const pendingMembers = members.filter((m) => m.status === 'PENDING');
  const assignedMembers = members.filter((m) => m.status === 'ASSIGNED');
  const vettedMembers = members.filter((m) => m.status === 'VETTED');
  const unsureMembers = members.filter((m) => m.status === 'UNSURE');
  const needsFollowUpMembers = members.filter((m) => m.status === 'NEEDS_FOLLOW_UP');
  const rejectedMembers = members.filter((m) => m.status === 'REJECTED');
  const processedMembers = members.filter((m) => m.status === 'PROCESSED');
  const archivedMembers = members.filter((m) => m.archived);
  const vetters = users.filter((u) => u.role === 'VETTER' && u.is_active);

  const statusSortOrder = {
    PENDING: 0,
    ASSIGNED: 1,
    VETTED: 2,
    UNSURE: 3,
    NEEDS_FOLLOW_UP: 4,
    REJECTED: 5,
    PROCESSED: 6,
  };

  const sortMembers = (memberList) => {
    return [...memberList].sort((a, b) => {
      if (sortMode === 'recent') {
        return new Date(b.updated_at) - new Date(a.updated_at);
      }
      if (sortMode === 'oldest') {
        return new Date(a.created_at) - new Date(b.created_at);
      }
      if (sortMode === 'name') {
        const nameA = `${a.last_name || ''} ${a.first_name || ''}`.toLowerCase();
        const nameB = `${b.last_name || ''} ${b.first_name || ''}`.toLowerCase();
        return nameA.localeCompare(nameB);
      }
      // 'status' sort: non-archived first, then by status priority, then by updated
      const aArchived = a.archived ? 1 : 0;
      const bArchived = b.archived ? 1 : 0;
      if (aArchived !== bArchived) return aArchived - bArchived;
      const aOrder = statusSortOrder[a.status] ?? 99;
      const bOrder = statusSortOrder[b.status] ?? 99;
      if (aOrder !== bOrder) return aOrder - bOrder;
      return new Date(b.updated_at) - new Date(a.updated_at);
    });
  };

  const applyAllFilters = (memberList) => {
    let filtered = memberList;
    if (statusFilter) {
      filtered = filtered.filter((m) => m.status === statusFilter);
    }
    filtered = filterByTags(filtered);
    return sortMembers(filtered);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header
        tabs={[
          { key: 'triage', label: `triage (${pendingMembers.length})` },
          { key: 'database', label: 'database' },
          { key: 'staff', label: 'staff' },
          { key: 'tags', label: 'tags' },
        ]}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          if (tab === 'tags' && tagCategories.length === 0) loadTagCategories();
        }}
        rightContent={
          (activeTab === 'database' || activeTab === 'triage') ? (
            <button
              onClick={handleReclaimStale}
              disabled={reclaimingStale}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              {reclaimingStale ? 'checking...' : 'reclaim stale'}
            </button>
          ) : null
        }
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">

        {/* Triage Tab */}
        {activeTab === 'triage' && (
          <div>
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
            {reclaimMessage && (
              <div className={`mb-3 p-2 rounded text-sm ${
                reclaimMessage.includes('Error') ? 'bg-red-100 text-red-700' :
                reclaimMessage.includes('0') ? 'bg-blue-100 text-blue-700' :
                'bg-green-100 text-green-700'
              }`}>
                {reclaimMessage}
              </div>
            )}

            {/* Search */}
            <div className="mb-3">
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
                <p className="text-sm text-gray-600 mt-1">Searching...</p>
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

            {/* Status pills */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              {[
                { key: 'PENDING', label: 'Pending', count: pendingMembers.length, bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300', activeBg: 'bg-yellow-200', ring: 'ring-yellow-400' },
                { key: 'ASSIGNED', label: 'Assigned', count: assignedMembers.length, bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300', activeBg: 'bg-blue-200', ring: 'ring-blue-400' },
                { key: 'VETTED', label: 'Vetted', count: vettedMembers.length, bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300', activeBg: 'bg-green-200', ring: 'ring-green-400' },
                { key: 'UNSURE', label: 'Unsure', count: unsureMembers.length, bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300', activeBg: 'bg-orange-200', ring: 'ring-orange-400' },
                { key: 'NEEDS_FOLLOW_UP', label: 'Follow-up', count: needsFollowUpMembers.length, bg: 'bg-pink-100', text: 'text-pink-800', border: 'border-pink-300', activeBg: 'bg-pink-200', ring: 'ring-pink-400' },
                { key: 'REJECTED', label: 'Rejected', count: rejectedMembers.length, bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300', activeBg: 'bg-red-200', ring: 'ring-red-400' },
                { key: 'PROCESSED', label: 'Processed', count: processedMembers.length, bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-300', activeBg: 'bg-purple-200', ring: 'ring-purple-400' },
              ].map((stat) => (
                <button
                  key={stat.key}
                  onClick={() => setStatusFilter(statusFilter === stat.key ? null : stat.key)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-full border cursor-pointer transition-all ${stat.text} ${
                    statusFilter === stat.key
                      ? `${stat.activeBg} ${stat.border} ring-2 ${stat.ring} shadow-sm`
                      : `${stat.bg} ${stat.border} hover:shadow-sm`
                  }`}
                >
                  {stat.label} <span className="font-bold">{stat.count}</span>
                </button>
              ))}
              <span className="text-gray-300 mx-0.5">|</span>
              <button
                onClick={() => setShowArchived(!showArchived)}
                className={`px-3 py-1.5 text-sm font-medium rounded-full border cursor-pointer transition-all text-gray-700 ${
                  showArchived
                    ? 'bg-gray-200 border-gray-400 ring-2 ring-gray-400 shadow-sm'
                    : 'bg-gray-100 border-gray-300 hover:shadow-sm'
                }`}
              >
                Archived <span className="font-bold">{archivedMembers.length}</span>
              </button>
            </div>

            {/* Selection controls row */}
            <div className="flex items-center gap-3 mb-3">
              <Button
                size="sm"
                onClick={() => {
                  if (selectMode) {
                    setSelectMode(false);
                    setSelectedMemberIds(new Set());
                  } else {
                    setSelectMode(true);
                  }
                }}
                variant={selectMode ? 'primary' : 'secondary'}
              >
                {selectMode ? 'Done' : 'Bulk Edit'}
              </Button>
              {selectMode && (
                <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(() => {
                      const visible = contactListMode
                        ? applyContactFilters(contacts)
                        : applyAllFilters(searchQuery ? searchResults : members);
                      return visible.length > 0 && visible.every((m) => selectedMemberIds.has(m.id));
                    })()}
                    onChange={() => {
                      const visible = contactListMode
                        ? applyContactFilters(contacts)
                        : applyAllFilters(searchQuery ? searchResults : members);
                      if (visible.every((m) => selectedMemberIds.has(m.id))) {
                        clearSelection();
                      } else {
                        selectAllVisible(visible);
                      }
                    }}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  Select All
                </label>
              )}
              {selectMode && selectedMemberIds.size > 0 && (
                <span className="text-sm text-primary-700 font-medium">
                  ({selectedMemberIds.size} selected)
                </span>
              )}
            </div>

            {/* Bulk Action Toolbar */}
            {selectMode && selectedMemberIds.size > 0 && (
              <div className="sticky top-0 z-10 bg-primary-50 border border-primary-200 rounded-lg p-3 mb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-primary-800">Actions:</span>
                  <Button size="sm" variant="secondary" onClick={() => confirmBulkAction({ type: 'status', value: 'VETTED', label: 'Vetted' })}>
                    Mark Vetted
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => confirmBulkAction({ type: 'status', value: 'PROCESSED', label: 'Processed' })}>
                    Mark Processed
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => confirmBulkAction({ type: 'status', value: 'PENDING', label: 'Pending' })}>
                    Mark Pending
                  </Button>
                  <div className="h-4 border-l border-primary-300" />
                  <Button size="sm" variant="secondary" onClick={() => confirmBulkAction({ type: 'archive', value: true, label: 'Archived' })}>
                    Archive
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => confirmBulkAction({ type: 'archive', value: false, label: 'Unarchived' })}>
                    Unarchive
                  </Button>
                </div>
                {tagConfig && tagConfig.categories.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-primary-200">
                    <span className="text-sm font-semibold text-primary-800">Set Tag:</span>
                    <select
                      value={bulkTagCategory}
                      onChange={(e) => { setBulkTagCategory(e.target.value); setBulkTagValue(''); }}
                      className="text-sm px-2 py-1 border border-gray-300 rounded-lg"
                    >
                      <option value="">Choose category...</option>
                      {tagConfig.categories.map((cat) => (
                        <option key={cat.key} value={cat.key}>{cat.label}</option>
                      ))}
                    </select>
                    {bulkTagCategory && (
                      <>
                        <select
                          value={bulkTagValue}
                          onChange={(e) => setBulkTagValue(e.target.value)}
                          className="text-sm px-2 py-1 border border-gray-300 rounded-lg"
                        >
                          <option value="">Choose value...</option>
                          {tagConfig.categories.find((c) => c.key === bulkTagCategory)?.options.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                        {bulkTagValue && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => {
                              const cat = tagConfig.categories.find((c) => c.key === bulkTagCategory);
                              confirmBulkAction({
                                type: 'tag',
                                tagKey: bulkTagCategory,
                                tagValue: bulkTagValue,
                                label: `tagged as ${cat?.label}: ${bulkTagValue}`,
                              });
                            }}
                          >
                            Apply Tag
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Results info row: count + sort + view toggle */}
            {(() => {
              const displayMembers = contactListMode
                ? applyContactFilters(contacts)
                : applyAllFilters(searchQuery ? searchResults : members);
              const totalCount = contactListMode ? displayMembers.length : displayMembers.length;
              const beforeFilterCount = searchQuery ? searchResults.length : members.length;
              const hasFilters = hasActiveTagFilters || statusFilter;
              return (
                <div className="flex items-center flex-wrap gap-x-4 gap-y-1 mb-3 text-sm text-gray-600">
                  <span>
                    {loading || loadingContacts ? 'Loading...' : `${totalCount} members`}
                    {searchQuery && !searching && hasFilters && ` (${beforeFilterCount} before filters)`}
                  </span>
                  <span className="flex-1" />
                  <span className="flex items-center gap-1 text-xs">
                    Sort:
                    {[
                      { value: 'recent', label: 'Recent' },
                      { value: 'oldest', label: 'Oldest' },
                      { value: 'name', label: 'Name' },
                      { value: 'status', label: 'Status' },
                    ].map((opt, i) => (
                      <span key={opt.value}>
                        {i > 0 && <span className="text-gray-300 mx-0.5">&middot;</span>}
                        <button
                          onClick={() => setSortMode(opt.value)}
                          className={`cursor-pointer transition-colors ${
                            sortMode === opt.value ? 'text-primary-600 font-semibold' : 'text-gray-500 hover:text-gray-700'
                          }`}
                        >
                          {opt.label}
                        </button>
                      </span>
                    ))}
                  </span>
                  <button
                    onClick={toggleContactListMode}
                    className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                      contactListMode
                        ? 'bg-primary-50 border-primary-300 text-primary-700'
                        : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
                    }`}
                  >
                    {contactListMode ? 'List' : 'Cards'}
                  </button>
                  {contactListMode && (
                    <button
                      onClick={handleCopyEmails}
                      disabled={loadingContacts}
                      className="px-2 py-0.5 text-xs rounded border border-gray-300 text-gray-600 hover:border-gray-400 transition-colors"
                    >
                      {copiedEmails ? 'Copied!' : 'Copy Emails'}
                    </button>
                  )}
                </div>
              );
            })()}

            {contactListMode ? (
              <div>
                <div className="bg-white shadow rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        {selectMode && (
                          <th className="px-2 py-3 w-8"></th>
                        )}
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
                          NEEDS_FOLLOW_UP: 'bg-pink-100 text-pink-800',
                          REJECTED: 'bg-red-100 text-red-800',
                          PROCESSED: 'bg-purple-100 text-purple-800',
                        };
                        return (
                          <tr
                            key={contact.id}
                            onClick={() => navigate(`/members/${contact.id}`, { state: { from: '/admin', tab: 'database' } })}
                            className="hover:bg-gray-50 cursor-pointer"
                          >
                            {selectMode && (
                              <td className="px-2 py-3 w-8" onClick={(e) => e.stopPropagation()}>
                                <input
                                  type="checkbox"
                                  checked={selectedMemberIds.has(contact.id)}
                                  onChange={() => toggleMemberSelection(contact.id)}
                                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                                />
                              </td>
                            )}
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
              <div>
                {(() => {
                  const displayMembers = applyAllFilters(searchQuery ? searchResults : members);
                  return (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {displayMembers.map((member, index) => (
                          <div key={member.id}>
                            {selectMode && (
                              <label
                                className="flex items-center gap-2 px-2 py-1 cursor-pointer"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedMemberIds.has(member.id)}
                                  onChange={() => toggleMemberSelection(member.id)}
                                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 w-4 h-4"
                                />
                                <span className="text-xs text-gray-500">
                                  {member.first_name} {member.last_name}
                                </span>
                              </label>
                            )}
                            <div className={selectMode && selectedMemberIds.has(member.id) ? 'ring-2 ring-primary-500 rounded-lg' : ''}>
                              <MemberCard
                                member={member}
                                tab="database"
                                searchContext={searchQuery ? {
                                  query: searchQuery,
                                  resultIds: displayMembers.map(m => m.id),
                                  currentIndex: index,
                                } : undefined}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {/* Tags Tab */}
        {activeTab === 'tags' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-900">Tag Management</h2>
              <Button onClick={openAddTagModal}>Add Category</Button>
            </div>
            {loadingTags ? (
              <p className="text-gray-600">Loading tag categories...</p>
            ) : tagCategories.length === 0 ? (
              <p className="text-gray-600">No tag categories configured.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tagCategories.map((cat) => (
                  <div key={cat.key} className="bg-white rounded-lg shadow p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">{cat.label}</h3>
                        <p className="text-sm text-gray-500 font-mono">{cat.key}</p>
                      </div>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        cat.multiple ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {cat.multiple ? 'Multi-select' : 'Single-select'}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {cat.options.map((option) => (
                        <span
                          key={option}
                          className="px-2.5 py-1 text-sm bg-gray-100 text-gray-700 rounded-full"
                        >
                          {option}
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2 border-t pt-3">
                      <Button size="sm" variant="secondary" onClick={() => openEditTagModal(cat)}>
                        Edit
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => openDeleteTagConfirm(cat)}>
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
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

      {/* Tag Add/Edit Modal */}
      <Modal
        isOpen={tagModalOpen}
        onClose={() => setTagModalOpen(false)}
        title={editingCategory ? `Edit Category: ${editingCategory.label}` : 'Add Tag Category'}
      >
        <div>
          {tagFormError && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {tagFormError}
            </div>
          )}
          <Input
            label="Key"
            name="tagKey"
            value={tagForm.key}
            onChange={(e) => setTagForm({ ...tagForm, key: e.target.value })}
            placeholder="e.g. interest_area"
            required
            disabled={!!editingCategory}
            className={editingCategory ? 'opacity-60' : ''}
          />
          <Input
            label="Label"
            name="tagLabel"
            value={tagForm.label}
            onChange={(e) => setTagForm({ ...tagForm, label: e.target.value })}
            placeholder="e.g. Interest Area"
            required
          />
          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                checked={tagForm.multiple}
                onChange={(e) => setTagForm({ ...tagForm, multiple: e.target.checked })}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              Allow multiple selections
            </label>
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Options <span className="text-red-500">*</span>
            </label>
            {tagForm.options.map((option, index) => (
              <div key={index} className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={option}
                  onChange={(e) => handleTagFormOptionChange(index, e.target.value)}
                  placeholder={`Option ${index + 1}`}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                {tagForm.options.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeTagFormOption(index)}
                    className="px-3 py-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addTagFormOption}
              className="text-sm text-primary-600 hover:text-primary-800 font-medium"
            >
              + Add option
            </button>
          </div>
          <Button onClick={handleTagFormSave} className="w-full">
            {editingCategory ? 'Save Changes' : 'Create Category'}
          </Button>
        </div>
      </Modal>

      {/* Bulk Action Confirmation Modal */}
      <Modal
        isOpen={bulkConfirmOpen}
        onClose={() => { setBulkConfirmOpen(false); setPendingBulkAction(null); }}
        title="Confirm Bulk Action"
      >
        <div>
          <p className="text-gray-700 mb-4">
            Are you sure you want to mark <strong>{selectedMemberIds.size}</strong> member{selectedMemberIds.size !== 1 ? 's' : ''} as{' '}
            <strong>{pendingBulkAction?.label}</strong>?
          </p>
          <div className="flex gap-3">
            <Button
              onClick={executeBulkAction}
              className="flex-1"
              disabled={bulkActionLoading}
            >
              {bulkActionLoading ? 'Updating...' : 'Confirm'}
            </Button>
            <Button
              onClick={() => { setBulkConfirmOpen(false); setPendingBulkAction(null); }}
              variant="secondary"
              className="flex-1"
              disabled={bulkActionLoading}
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>

      {/* Tag Delete Confirmation Modal */}
      <Modal
        isOpen={tagDeleteConfirmOpen}
        onClose={() => { setTagDeleteConfirmOpen(false); setCategoryToDelete(null); }}
        title="Delete Tag Category"
      >
        <div>
          <p className="text-gray-700 mb-4">
            Are you sure you want to delete the <strong>{categoryToDelete?.label}</strong> category?
          </p>
          {loadingUsage ? (
            <p className="text-sm text-gray-500 mb-4">Checking usage...</p>
          ) : deleteUsage && deleteUsage.total_members_using > 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
              <p className="text-sm font-medium text-yellow-800 mb-2">
                {deleteUsage.total_members_using} member{deleteUsage.total_members_using !== 1 ? 's' : ''} currently use tags from this category:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(deleteUsage.usage).filter(([, count]) => count > 0).map(([option, count]) => (
                  <span key={option} className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">
                    {option}: {count}
                  </span>
                ))}
              </div>
              <p className="text-xs text-yellow-700 mt-2">
                Existing member data will be preserved, but this category will no longer appear as a choice.
              </p>
            </div>
          ) : deleteUsage ? (
            <p className="text-sm text-gray-500 mb-4">No members are using tags from this category.</p>
          ) : null}
          <div className="flex gap-3">
            <Button
              onClick={handleDeleteTagConfirm}
              className="flex-1 bg-red-600 hover:bg-red-700"
              disabled={loadingUsage}
            >
              Delete
            </Button>
            <Button
              onClick={() => { setTagDeleteConfirmOpen(false); setCategoryToDelete(null); }}
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
