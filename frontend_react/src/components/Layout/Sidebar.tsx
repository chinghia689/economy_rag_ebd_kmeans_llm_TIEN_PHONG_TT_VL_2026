import { useChatStore } from '../../domains/chat/chatStore';
import { useAuthStore } from '../../domains/auth/authStore';
import {
  HiOutlinePlus,
  HiOutlineTrash,
  HiOutlineChatBubbleLeftRight,
  HiOutlineArrowRightOnRectangle,
  HiOutlineCreditCard,
  HiOutlineCircleStack,
  HiOutlineSun,
  HiOutlineMoon,
} from 'react-icons/hi2';
import { useState } from 'react';

interface SidebarProps {
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenPayment: () => void;
  onOpenLogin: () => void;
}

export default function Sidebar({ isDark, onToggleTheme, onOpenPayment, onOpenLogin }: SidebarProps) {
  const {
    conversations,
    activeConversationId,
    createConversation,
    setActiveConversation,
    deleteConversation,
    clearAllConversations,
  } = useChatStore();

  const { user, isAuthenticated, tokenBalance, logout } = useAuthStore();
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <aside className="flex flex-col h-full w-[300px] border-r border-[var(--border-color)] bg-[var(--bg-secondary)]">
      {/* ── Header ── */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <h1 className="text-lg font-bold bg-gradient-to-r from-[#667eea] to-[#764ba2] bg-clip-text text-transparent">
          🇻🇳 Chatbot Kinh Tế
        </h1>
        <p className="text-xs text-[var(--text-muted)] mt-1">RAG + Energy-Based Distance</p>
      </div>

      {/* ── New Chat Button ── */}
      <div className="p-3">
        <button
          id="btn-new-chat"
          onClick={() => void createConversation()}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl
                     border border-dashed border-[var(--border-color)]
                     hover:border-[var(--accent-primary)] hover:bg-[var(--bg-hover)]
                     transition-all duration-200 text-sm text-[var(--text-secondary)]
                     hover:text-[var(--text-primary)] cursor-pointer group"
        >
          <HiOutlinePlus className="w-4 h-4 group-hover:text-[var(--accent-primary)] transition-colors" />
          <span>Cuộc hội thoại mới</span>
        </button>
      </div>

      {/* ── Conversation List ── */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {conversations.length === 0 && (
          <div className="text-center py-8 text-[var(--text-muted)] text-xs">
            Chưa có cuộc hội thoại nào
          </div>
        )}
        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => setActiveConversation(conv.id)}
            onMouseEnter={() => setHoveredId(conv.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={`
              w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left text-sm
              transition-all duration-200 cursor-pointer group relative
              ${
                activeConversationId === conv.id
                  ? 'bg-[var(--bg-hover)] text-[var(--text-primary)] border border-[var(--accent-primary)]/30'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] border border-transparent'
              }
            `}
          >
            <HiOutlineChatBubbleLeftRight className="w-4 h-4 flex-shrink-0 text-[var(--accent-primary)]" />
            <span className="truncate flex-1">{conv.title}</span>

            {/* Delete button on hover */}
            {hoveredId === conv.id && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  void deleteConversation(conv.id);
                }}
                className="absolute right-2 p-1 rounded-lg hover:bg-red-500/20 text-[var(--text-muted)]
                           hover:text-red-400 transition-all"
              >
                <HiOutlineTrash className="w-3.5 h-3.5" />
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Bottom Actions ── */}
      <div className="p-3 border-t border-[var(--border-color)] space-y-2">
        {/* Dark mode toggle */}
        <button
          id="btn-toggle-theme"
          onClick={onToggleTheme}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm
                     text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]
                     hover:text-[var(--text-primary)] transition-all cursor-pointer"
        >
          {isDark ? <HiOutlineSun className="w-4 h-4" /> : <HiOutlineMoon className="w-4 h-4" />}
          <span>{isDark ? 'Chế độ sáng' : 'Chế độ tối'}</span>
        </button>

        {/* Payment */}
        {isAuthenticated && (
          <div className="px-3 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)]">
            <div className="flex items-center gap-2 text-sm text-[var(--text-primary)]">
              <HiOutlineCircleStack className="w-4 h-4 text-[var(--accent-primary)]" />
              <span className="flex-1">Token còn lại</span>
              <span className="font-semibold">{tokenBalance ?? '...'}</span>
            </div>
          </div>
        )}

        {isAuthenticated && (
          <button
            id="btn-open-payment"
            onClick={onOpenPayment}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm
                       text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]
                       hover:text-[var(--text-primary)] transition-all cursor-pointer"
          >
            <HiOutlineCreditCard className="w-4 h-4" />
            <span>Nạp Token</span>
          </button>
        )}

        {!isAuthenticated && (
          <div className="px-3 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)]
                          text-xs text-[var(--text-muted)] leading-relaxed">
            Guest mode: lịch sử chỉ lưu trên thiết bị này.
          </div>
        )}

        {/* Clear all */}
        {conversations.length > 0 && (
          <button
            id="btn-clear-all"
            onClick={() => void clearAllConversations()}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm
                       text-[var(--text-muted)] hover:bg-red-500/10
                       hover:text-red-400 transition-all cursor-pointer"
          >
            <HiOutlineTrash className="w-4 h-4" />
            <span>Xóa tất cả</span>
          </button>
        )}

        {/* User info / Login */}
        <div className="pt-2 border-t border-[var(--border-color)]">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2.5">
              {user.picture ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  className="w-8 h-8 rounded-full border border-[var(--border-color)]"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#667eea] to-[#764ba2]
                                flex items-center justify-center text-xs font-bold text-white">
                  {user.name?.[0]?.toUpperCase() || '?'}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">{user.name}</p>
                <p className="text-[10px] text-[var(--text-muted)] truncate">{user.email}</p>
              </div>
              <button
                id="btn-logout"
                onClick={logout}
                className="p-1.5 rounded-lg hover:bg-red-500/20 text-[var(--text-muted)]
                           hover:text-red-400 transition-all cursor-pointer"
                title="Đăng xuất"
              >
                <HiOutlineArrowRightOnRectangle className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              id="btn-login"
              onClick={onOpenLogin}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                         bg-gradient-to-r from-[#667eea] to-[#764ba2] text-white text-sm font-medium
                         hover:opacity-90 transition-opacity cursor-pointer"
            >
              Đăng nhập với Google
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
