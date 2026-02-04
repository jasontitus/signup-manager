import client from './client';

export const membersAPI = {
  // Public application submission
  submitApplication: async (data) => {
    const response = await client.post('/public/apply', data);
    return response.data;
  },

  // List members (filtered by role)
  list: async (statusFilter = null) => {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    const response = await client.get('/members', { params });
    return response.data;
  },

  // Get member detail (with decrypted PII)
  get: async (id) => {
    const response = await client.get(`/members/${id}`);
    return response.data;
  },

  // Assign member to vetter
  assign: async (memberId, vetterId) => {
    const response = await client.patch(`/members/${memberId}/assign`, {
      vetter_id: vetterId,
    });
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
};
