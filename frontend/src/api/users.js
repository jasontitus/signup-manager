import client from './client';

export const usersAPI = {
  list: async () => {
    const response = await client.get('/users');
    return response.data;
  },

  create: async (userData) => {
    const response = await client.post('/users', userData);
    return response.data;
  },

  get: async (id) => {
    const response = await client.get(`/users/${id}`);
    return response.data;
  },

  update: async (id, userData) => {
    const response = await client.patch(`/users/${id}`, userData);
    return response.data;
  },

  delete: async (id) => {
    await client.delete(`/users/${id}`);
  },
};
