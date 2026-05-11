import { create } from 'zustand';
import {
  createConversation as createConversationApi,
  deleteConversation as deleteConversationApi,
  getConversationMessages,
  listConversations,
} from '../../services/api';
import type { Message, Conversation, Source, ServerConversation, ServerMessage } from '../../types';

interface ChatState {
  /* ── Conversations ── */
  conversations: Conversation[];
  activeConversationId: string | null;

  /* ── UI State ── */
  isSending: boolean;
  error: string | null;

  /* ── Actions ── */
  loadGuestState: () => void;
  loadServerConversations: () => Promise<void>;
  createConversation: () => Promise<string>;
  setActiveConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  clearAllConversations: () => Promise<void>;

  addMessage: (msg: Message) => void;
  updateLastBotMessage: (content: string, sources?: Source[], responseTime?: number, tokenUsed?: number) => void;
  setConversationMessages: (conversationId: string, messages: Message[], conversation?: Conversation) => void;
  upsertConversation: (conversation: Conversation) => void;

  setIsSending: (v: boolean) => void;
  setError: (e: string | null) => void;

  /* ── Computed ── */
  getActiveMessages: () => Message[];
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substring(2, 8);
}

function generateTitle(firstMsg: string): string {
  const clean = firstMsg.replace(/\n/g, ' ').trim();
  return clean.length > 40 ? clean.substring(0, 40) + '...' : clean;
}

function hasAuthToken(): boolean {
  return Boolean(localStorage.getItem('jwt_token'));
}

function saveToStorage(conversations: Conversation[], activeId: string | null) {
  if (hasAuthToken()) return;
  try {
    localStorage.setItem('chat_conversations', JSON.stringify(conversations));
    localStorage.setItem('chat_active_id', activeId || '');
  } catch { /* ignore storage errors */ }
}

function loadFromStorage(): { conversations: Conversation[]; activeId: string | null } {
  try {
    const convRaw = localStorage.getItem('chat_conversations');
    const activeId = localStorage.getItem('chat_active_id') || null;
    const conversations = convRaw ? JSON.parse(convRaw) : [];
    return { conversations, activeId };
  } catch {
    return { conversations: [], activeId: null };
  }
}

function serverConversationToConversation(conv: ServerConversation, messages: Message[] = []): Conversation {
  return {
    id: conv.id,
    title: conv.title,
    messages,
    createdAt: Date.parse(conv.created_at),
    updatedAt: Date.parse(conv.updated_at),
  };
}

function serverMessageToMessage(msg: ServerMessage): Message {
  return {
    id: String(msg.id),
    role: msg.role,
    content: msg.content,
    sources: msg.sources,
    tokenUsed: msg.token_used,
    responseTime: msg.response_time,
    timestamp: Date.parse(msg.created_at),
  };
}

const stored = loadFromStorage();

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: stored.conversations,
  activeConversationId: stored.activeId,
  isSending: false,
  error: null,

  loadGuestState: () => {
    const guest = loadFromStorage();
    set({
      conversations: guest.conversations,
      activeConversationId: guest.activeId,
      isSending: false,
      error: null,
    });
  },

  loadServerConversations: async () => {
    const res = await listConversations();
    const conversations = res.data?.conversations.map((conv) => serverConversationToConversation(conv)) || [];
    const activeConversationId = conversations[0]?.id || null;
    set({ conversations, activeConversationId });

    if (activeConversationId) {
      await get().setActiveConversation(activeConversationId);
    }
  },

  createConversation: async () => {
    if (hasAuthToken()) {
      const res = await createConversationApi();
      const serverConversation = res.data?.conversation;
      if (!serverConversation) {
        throw new Error(res.message || 'Không thể tạo hội thoại.');
      }
      const conv = serverConversationToConversation(serverConversation);
      set((state) => ({
        conversations: [conv, ...state.conversations.filter((item) => item.id !== conv.id)],
        activeConversationId: conv.id,
      }));
      return conv.id;
    }

    const id = generateId();
    const conv: Conversation = {
      id,
      title: 'Cuộc hội thoại mới',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    set((state) => {
      const conversations = [conv, ...state.conversations];
      saveToStorage(conversations, id);
      return { conversations, activeConversationId: id };
    });

    return id;
  },

  setActiveConversation: async (id) => {
    set({ activeConversationId: id });
    const { conversations } = get();
    saveToStorage(conversations, id);

    if (hasAuthToken()) {
      const res = await getConversationMessages(id);
      const messages = res.data?.messages.map(serverMessageToMessage) || [];
      get().setConversationMessages(id, messages);
    }
  },

  deleteConversation: async (id) => {
    if (hasAuthToken()) {
      await deleteConversationApi(id);
    }

    set((state) => {
      const conversations = state.conversations.filter((c) => c.id !== id);
      const activeConversationId =
        state.activeConversationId === id
          ? conversations[0]?.id || null
          : state.activeConversationId;
      saveToStorage(conversations, activeConversationId);
      return { conversations, activeConversationId };
    });
  },

  clearAllConversations: async () => {
    if (hasAuthToken()) {
      await Promise.all(get().conversations.map((conv) => deleteConversationApi(conv.id)));
    }
    set({ conversations: [], activeConversationId: null });
    saveToStorage([], null);
  },

  addMessage: (msg) => {
    set((state) => {
      const convId = state.activeConversationId;
      if (!convId) return state;

      const conversations = state.conversations.map((c) => {
        if (c.id !== convId) return c;

        const messages = [...c.messages, msg];
        const title = c.messages.length === 0 && msg.role === 'user'
          ? generateTitle(msg.content)
          : c.title;

        return { ...c, messages, title, updatedAt: Date.now() };
      });

      saveToStorage(conversations, convId);
      return { conversations };
    });
  },

  updateLastBotMessage: (content, sources, responseTime, tokenUsed) => {
    set((state) => {
      const convId = state.activeConversationId;
      if (!convId) return state;

      const conversations = state.conversations.map((c) => {
        if (c.id !== convId) return c;

        const messages = [...c.messages];
        const lastIdx = messages.length - 1;
        if (lastIdx >= 0 && messages[lastIdx].role === 'bot') {
          messages[lastIdx] = {
            ...messages[lastIdx],
            content,
            sources: sources || messages[lastIdx].sources,
            responseTime: responseTime ?? messages[lastIdx].responseTime,
            tokenUsed: tokenUsed ?? messages[lastIdx].tokenUsed,
          };
        }

        return { ...c, messages, updatedAt: Date.now() };
      });

      saveToStorage(conversations, convId);
      return { conversations };
    });
  },

  setConversationMessages: (conversationId, messages, conversation) => {
    set((state) => {
      const conversations = state.conversations.map((item) => {
        if (item.id !== conversationId) return item;
        return {
          ...(conversation || item),
          messages,
        };
      });
      saveToStorage(conversations, state.activeConversationId);
      return { conversations };
    });
  },

  upsertConversation: (conversation) => {
    set((state) => {
      const conversations = [
        conversation,
        ...state.conversations.filter((item) => item.id !== conversation.id),
      ];
      saveToStorage(conversations, state.activeConversationId || conversation.id);
      return { conversations };
    });
  },

  setIsSending: (v) => set({ isSending: v }),
  setError: (e) => set({ error: e }),

  getActiveMessages: () => {
    const { conversations, activeConversationId } = get();
    if (!activeConversationId) return [];
    const conv = conversations.find((c) => c.id === activeConversationId);
    return conv?.messages || [];
  },
}));
