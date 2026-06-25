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
  HiOutlineHome,
  HiOutlineInformationCircle,
  HiOutlineShieldCheck,
  HiOutlineClock,
  HiOutlineMagnifyingGlass,
  HiOutlinePencilSquare,
  HiOutlineBookmark,
  HiOutlineBookmarkSlash,
  HiOutlineCurrencyDollar,
} from 'react-icons/hi2';
import { useState } from 'react';
import { NavLink } from 'react-router-dom';

interface SidebarProps {
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenPayment: () => void;
  onOpenLogin: () => void;
  onOpenTransactions: () => void;
  onOpenDeleteAccount: () => void;
}

export default function Sidebar({ isDark, onToggleTheme, onOpenPayment, onOpenLogin, onOpenTransactions, onOpenDeleteAccount }: SidebarProps) {
  const {
    conversations,
    activeConversationId,
    createConversation,
    setActiveConversation,
    deleteConversation,
    clearAllConversations,
    renameConversation,
    togglePinConversation,
  } = useChatStore();

  const { user, isAuthenticated, tokenBalance, logout } = useAuthStore();
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [conversationSearch, setConversationSearch] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(conversationSearch.trim().toLowerCase())
  );

  return (
    <aside className="flex h-full min-h-0 w-[300px] flex-col overflow-hidden border-r border-[var(--border-color)] bg-[var(--bg-secondary)]">
      {/* ── Header ── */}
      <div className="flex-none p-4 border-b border-[var(--border-color)]">
        <h1 className="flex items-center gap-2 text-lg font-bold text-[var(--text-primary)]">
          <span className="text-xl" aria-hidden="true">🇻🇳</span>
          <span>Chatbot Kinh Tế</span>
        </h1>
        <p className="text-xs text-[var(--text-muted)] mt-1">GT1 Single-Vector ERC</p>
      </div>


      {/* ── Primary Navigation ── */}
      <nav className="flex-none px-3 pt-3 space-y-1">
        {[
          { to: '/', label: 'Trang chủ', icon: HiOutlineHome, end: true },
          { to: '/chat', label: 'Chat', icon: HiOutlineChatBubbleLeftRight },
          { to: '/about', label: 'Giới thiệu', icon: HiOutlineInformationCircle },
          { to: '/pricing', label: 'Bảng giá', icon: HiOutlineCurrencyDollar },
          ...(user?.is_admin ? [{ to: '/admin', label: 'Admin', icon: HiOutlineShieldCheck }] : []),
        ].map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `
                flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition-all
                ${isActive
                  ? 'bg-[var(--bg-hover)] text-[var(--text-primary)] border border-[var(--accent-primary)]/30'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] border border-transparent'
                }
              `}
            >
              <Icon className="h-4 w-4 text-[var(--accent-primary)]" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* ── New Chat Button ── */}
      <div className="flex-none p-3">
        <button
          id="btn-new-chat"
          onClick={() => {
            if (!isAuthenticated) {
              onOpenLogin();
              return;
            }
            void createConversation();
          }}
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

      <div className="flex-none px-3 pb-2">
        <div className="relative">
          <HiOutlineMagnifyingGlass className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            value={conversationSearch}
            onChange={(event) => setConversationSearch(event.target.value)}
            className="h-9 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] pl-9 pr-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]"
            placeholder="Tìm hội thoại"
          />
        </div>
      </div>

      {/* ── Conversation List ── */}
      <div className="min-h-0 flex-1 overflow-y-auto px-2 space-y-1 overscroll-contain">
        {filteredConversations.length === 0 && (
          <div className="text-center py-8 text-[var(--text-muted)] text-xs">
            {conversations.length === 0 ? 'Chưa có cuộc hội thoại nào' : 'Không tìm thấy hội thoại'}
          </div>
        )}
        {filteredConversations.map((conv) => (
          <div
            key={conv.id}
            onMouseEnter={() => setHoveredId(conv.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={`
              group relative rounded-xl border text-sm transition-all duration-200
              ${
                activeConversationId === conv.id
                  ? 'bg-[var(--bg-hover)] text-[var(--text-primary)] border-[var(--accent-primary)]/30'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] border-transparent'
              }
            `}
          >
            {editingId === conv.id ? (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void renameConversation(conv.id, editingTitle).finally(() => setEditingId(null));
                }}
                className="flex items-center gap-2 px-2 py-2"
              >
                <input
                  value={editingTitle}
                  onChange={(event) => setEditingTitle(event.target.value)}
                  autoFocus
                  className="min-w-0 flex-1 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-2 py-1 text-xs outline-none focus:border-[var(--accent-primary)]"
                />
                <button className="rounded-lg px-2 py-1 text-xs text-emerald-300 hover:bg-emerald-500/10">Lưu</button>
              </form>
            ) : (
              <button
                onClick={() => setActiveConversation(conv.id)}
                className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left"
              >
                <HiOutlineChatBubbleLeftRight className="h-4 w-4 flex-shrink-0 text-[var(--accent-primary)]" />
                {conv.isPinned && <HiOutlineBookmark className="h-3.5 w-3.5 flex-shrink-0 text-amber-300" />}
                <span className="min-w-0 flex-1 truncate">{conv.title}</span>
              </button>
            )}

            {hoveredId === conv.id && editingId !== conv.id && (
              <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-lg bg-[var(--bg-hover)] px-1">
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    togglePinConversation(conv.id);
                  }}
                  className="rounded-md p-1 text-[var(--text-muted)] hover:text-amber-300"
                  title={conv.isPinned ? 'Bỏ ghim' : 'Ghim'}
                >
                  {conv.isPinned ? <HiOutlineBookmarkSlash className="h-3.5 w-3.5" /> : <HiOutlineBookmark className="h-3.5 w-3.5" />}
                </button>
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    setEditingId(conv.id);
                    setEditingTitle(conv.title);
                  }}
                  className="rounded-md p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                  title="Đổi tên"
                >
                  <HiOutlinePencilSquare className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    void deleteConversation(conv.id);
                  }}
                  className="rounded-md p-1 text-[var(--text-muted)] hover:text-red-400"
                  title="Xóa"
                >
                  <HiOutlineTrash className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── Bottom Actions ── */}
      <div className="h-[250px] max-h-[45dvh] flex-none overflow-y-auto overscroll-contain p-3 border-t border-[var(--border-color)] space-y-2">
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
              <span className="flex-1">Credit còn lại</span>
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
            <span>Nạp credit</span>
          </button>
        )}


        {isAuthenticated && (
          <button
            id="btn-open-transactions"
            onClick={onOpenTransactions}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm
                       text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]
                       hover:text-[var(--text-primary)] transition-all cursor-pointer"
          >
            <HiOutlineClock className="w-4 h-4" />
            <span>Lịch sử giao dịch</span>
          </button>
        )}

        {isAuthenticated && (
          <button
            id="btn-delete-account"
            onClick={onOpenDeleteAccount}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm text-red-300 hover:bg-red-500/10 hover:text-red-200 transition-all cursor-pointer"
          >
            <HiOutlineTrash className="w-4 h-4" />
            <span>Xóa tài khoản</span>
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
