import { create } from 'zustand';
import { api } from '../api/client';

export const useAuthStore = create((set, get) => ({
  user: null,
  token: localStorage.getItem('token') || null,

  isAuthenticated: () => !!get().token,

  login: async (email, password) => {
    const data = await api.postForm(
      '/auth/login',
      new URLSearchParams({ username: email, password })
    );
    const token = data.access_token;
    localStorage.setItem('token', token);
    set({ token });
    await get().checkAuth();
  },

  register: async (email, password) => {
    await api.post('/auth/register', { email, password });
    await get().login(email, password);
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, user: null });
  },

  checkAuth: async () => {
    try {
      const user = await api.get('/auth/me');
      set({ user });
    } catch {
      get().logout();
    }
  },
}));
