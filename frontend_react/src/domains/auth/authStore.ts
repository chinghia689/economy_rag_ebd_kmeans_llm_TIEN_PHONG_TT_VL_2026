import { create } from 'zustand';
import type { TokenTransaction, User } from '../../types';
import { getBalance, getMe } from '../../services/api';
import { useChatStore } from '../chat/chatStore';

interface AuthState {
  user: User | null;
  token: string | null;
  tokenBalance: number | null;
  tokenTransactions: TokenTransaction[];
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (token: string, user: User) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  refreshBalance: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('jwt_token'),
  tokenBalance: null,
  tokenTransactions: [],
  isLoading: true,
  isAuthenticated: false,

  login: async (token, user) => {
    localStorage.setItem('jwt_token', token);
    set({ token, user, isAuthenticated: true, isLoading: false });

    const me = await getMe();
    const balance = await getBalance();
    set({
      user: me.data || user,
      tokenBalance: balance.data?.token_balance ?? null,
      tokenTransactions: balance.data?.transactions || [],
      isAuthenticated: true,
      isLoading: false,
    });
    await useChatStore.getState().loadServerConversations();
  },

  logout: () => {
    localStorage.removeItem('jwt_token');
    set({
      token: null,
      user: null,
      tokenBalance: null,
      tokenTransactions: [],
      isAuthenticated: false,
      isLoading: false,
    });
    useChatStore.getState().loadGuestState();
  },

  checkAuth: async () => {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      useChatStore.getState().loadGuestState();
      return;
    }
    try {
      const res = await getMe();
      const balance = await getBalance();
      if (res.success && res.data) {
        set({
          user: res.data,
          token,
          tokenBalance: balance.data?.token_balance ?? null,
          tokenTransactions: balance.data?.transactions || [],
          isAuthenticated: true,
          isLoading: false,
        });
        await useChatStore.getState().loadServerConversations();
      } else {
        localStorage.removeItem('jwt_token');
        set({ isLoading: false, isAuthenticated: false });
        useChatStore.getState().loadGuestState();
      }
    } catch {
      localStorage.removeItem('jwt_token');
      set({
        token: null,
        user: null,
        tokenBalance: null,
        tokenTransactions: [],
        isLoading: false,
        isAuthenticated: false,
      });
      useChatStore.getState().loadGuestState();
    }
  },

  refreshBalance: async () => {
    const res = await getBalance();
    if (res.success && res.data) {
      set({
        tokenBalance: res.data.token_balance,
        tokenTransactions: res.data.transactions,
      });
    }
  },
}));
