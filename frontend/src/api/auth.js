import client from './client';

export const authAPI = {
  login: async (username, password) => {
    const response = await client.post('/auth/login', {
      username,
      password,
    });
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },
};
