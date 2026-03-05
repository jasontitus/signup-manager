import client from './client';

export const membersAPI = {
  // Public application submission
  submitApplication: async (data) => {
    const response = await client.post('/public/apply', data);
    return response.data;
  },

  // List members (filtered by role)
  list: async (statusFilter = null, includeArchived = false) => {
    const params = {};
    if (statusFilter) params.status_filter = statusFilter;
    if (includeArchived) params.include_archived = true;
    const response = await client.get('/members', { params });
    return response.data;
  },

  // Search members
  search: async (query) => {
    const response = await client.get('/members/search/query', {
      params: { q: query }
    });
    return response.data;
  },

  // Get member detail (with decrypted PII)
  get: async (id) => {
    const response = await client.get(`/members/${id}`);
    return response.data;
  },

  // Update member status
  updateStatus: async (memberId, status) => {
    const response = await client.patch(`/members/${memberId}/status`, {
      status,
    });
    return response.data;
  },

  // Add note to member
  addNote: async (memberId, note) => {
    const response = await client.post(`/members/${memberId}/notes`, {
      note,
    });
    return response.data;
  },

  // Get count of pending candidates in the queue
  getQueueCount: async () => {
    const response = await client.get('/members/queue-count');
    return response.data;
  },

  // Get next pending candidate (auto-assigns to current vetter)
  getNextCandidate: async () => {
    const response = await client.post('/members/next-candidate');
    return response.data;
  },

  // Reclaim stale assignments (admin only)
  reclaimStaleAssignments: async () => {
    const response = await client.post('/members/reclaim-stale');
    return response.data;
  },

  // Update member tags
  updateTags: async (memberId, tags) => {
    const response = await client.patch(`/members/${memberId}/tags`, { tags });
    return response.data;
  },

  // Update archived flag
  updateArchived: async (memberId, archived) => {
    const response = await client.patch(`/members/${memberId}/archive`, {
      archived,
    });
    return response.data;
  },

  // Update custom fields (merge semantics)
  updateCustomFields: async (memberId, customFields) => {
    const response = await client.patch(`/members/${memberId}/custom-fields`, {
      custom_fields: customFields,
    });
    return response.data;
  },

  // Bulk update status (admin only)
  bulkUpdateStatus: async (memberIds, status) => {
    const response = await client.patch('/members/bulk-status', {
      member_ids: memberIds,
      status,
    });
    return response.data;
  },

  // Bulk update archived flag (admin only)
  bulkUpdateArchived: async (memberIds, archived) => {
    const response = await client.patch('/members/bulk-archive', {
      member_ids: memberIds,
      archived,
    });
    return response.data;
  },

  // Bulk update tags (admin only)
  bulkUpdateTags: async (memberIds, tagKey, tagValue) => {
    const response = await client.patch('/members/bulk-tags', {
      member_ids: memberIds,
      tag_key: tagKey,
      tag_value: tagValue,
    });
    return response.data;
  },

  // Get contacts list (admin only)
  getContacts: async (params = {}) => {
    const response = await client.get('/members/contacts', { params });
    return response.data;
  },

  // Delete member (admin only)
  delete: async (memberId) => {
    const response = await client.delete(`/members/${memberId}`);
    return response.data;
  },
};
