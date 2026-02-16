import client from './client';

export const tagsAPI = {
  getConfig: async () => {
    const response = await client.get('/tags');
    return response.data;
  },

  addCategory: async (category) => {
    const response = await client.post('/tags/categories', category);
    return response.data;
  },

  updateCategory: async (key, data) => {
    const response = await client.put(`/tags/categories/${key}`, data);
    return response.data;
  },

  deleteCategory: async (key) => {
    const response = await client.delete(`/tags/categories/${key}`);
    return response.data;
  },

  getOptionUsage: async (key) => {
    const response = await client.get(`/tags/categories/${key}/usage`);
    return response.data;
  },
};
