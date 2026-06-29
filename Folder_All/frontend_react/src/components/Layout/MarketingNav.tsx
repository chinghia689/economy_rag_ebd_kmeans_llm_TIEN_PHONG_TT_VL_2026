import { Link, NavLink } from 'react-router-dom';
import {
  HiOutlineArrowRightOnRectangle,
  HiOutlineChatBubbleLeftRight,
  HiOutlineCreditCard,
  HiOutlineClock,
  HiOutlineMoon,
  HiOutlineShieldCheck,
  HiOutlineSun,
  HiOutlineTrash,
} from 'react-icons/hi2';
import { useAuthStore } from '../../domains/auth/authStore';

interface MarketingNavProps {
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenLogin: () => void;
  onOpenPayment: () => void;
  onOpenTransactions: () => void;
  onOpenDeleteAccount: () => void;
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm transition-colors ${
    isActive
      ? 'text-[var(--text-primary)]'
      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
  }`;

export default function MarketingNav({
  isDark,
  onToggleTheme,
  onOpenLogin,
  onOpenPayment,
  onOpenTransactions,
  onOpenDeleteAccount,
}: MarketingNavProps) {
  const { user, isAuthenticated, logout } = useAuthStore();

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] text-xs font-bold">
            KT
          </span>
          <span>Chatbot Kinh Tế</span>
        </Link>

        <nav className="ml-8 hidden items-center gap-6 md:flex">
          <NavLink to="/" className={navLinkClass} end>
            Trang chủ
          </NavLink>
          <NavLink to="/about" className={navLinkClass}>
            Giới thiệu
          </NavLink>
          <NavLink to="/chat" className={navLinkClass}>
            Chat
          </NavLink>
          <NavLink to="/pricing" className={navLinkClass}>
            Bảng giá
          </NavLink>
          <NavLink to="/security" className={navLinkClass}>
            Bảo mật
          </NavLink>

          {isAuthenticated && (
            <button
              onClick={onOpenTransactions}
              className="hidden h-9 items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] md:flex"
            >
              <HiOutlineClock className="h-4 w-4" />
              Lịch sử
            </button>
          )}

          {user?.is_admin && (
            <NavLink to="/admin" className={navLinkClass}>
              Admin
            </NavLink>
          )}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={onToggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            title={isDark ? 'Chế độ sáng' : 'Chế độ tối'}
          >
            {isDark ? <HiOutlineSun className="h-4 w-4" /> : <HiOutlineMoon className="h-4 w-4" />}
          </button>

          {isAuthenticated && (
            <button
              onClick={onOpenPayment}
              className="hidden h-9 items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] sm:flex"
            >
              <HiOutlineCreditCard className="h-4 w-4" />
              Nạp credit
            </button>
          )}

          {user?.is_admin && (
            <Link
              to="/admin"
              className="hidden h-9 items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] lg:flex"
            >
              <HiOutlineShieldCheck className="h-4 w-4" />
              Admin
            </Link>
          )}

          <Link
            to="/chat"
            className="flex h-9 items-center gap-2 rounded-lg bg-[var(--text-primary)] px-3 text-sm font-medium text-[var(--bg-primary)] transition-opacity hover:opacity-90"
          >
            <HiOutlineChatBubbleLeftRight className="h-4 w-4" />
            Chat
          </Link>

          {isAuthenticated ? (
            <>
              <button
                onClick={onOpenDeleteAccount}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-secondary)] transition-colors hover:bg-red-500/10 hover:text-red-400"
                title="Xóa tài khoản"
              >
                <HiOutlineTrash className="h-4 w-4" />
              </button>
              <button
                onClick={logout}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-secondary)] transition-colors hover:bg-red-500/10 hover:text-red-400"
                title="Đăng xuất"
              >
                <HiOutlineArrowRightOnRectangle className="h-4 w-4" />
              </button>
            </>
          ) : (
            <button
              onClick={onOpenLogin}
              className="hidden h-9 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] sm:block"
            >
              Đăng nhập
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
