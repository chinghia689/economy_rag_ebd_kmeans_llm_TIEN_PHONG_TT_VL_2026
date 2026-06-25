import { useCallback, useState, useEffect, ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Sidebar from './components/Layout/Sidebar';
import MarketingNav from './components/Layout/MarketingNav';
import Footer from './components/Layout/Footer';
import ChatPage from './domains/chat/pages/ChatPage';
import LoginModal from './domains/auth/components/LoginModal';
import DeleteAccountModal from './domains/auth/components/DeleteAccountModal';
import PaymentModal from './domains/payment/components/PaymentModal';
import TransactionHistoryModal from './domains/payment/components/TransactionHistoryModal';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import PricingPage from './pages/PricingPage';
import InfoPage from './pages/InfoPage';
import PublicContentPage from './pages/PublicContentPage';
import AdminPage from './domains/admin/pages/AdminPage';
import { useAuthStore } from './domains/auth/authStore';
import { HiOutlineBars3 } from 'react-icons/hi2';
import { getPublicContent } from './services/api';
import { DEFAULT_PUBLIC_CONTENT } from './content/publicContent';

interface MarketingFrameProps {
  children: ReactNode;
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenLogin: () => void;
  onOpenPayment: () => void;
  onOpenTransactions: () => void;
  onOpenDeleteAccount: () => void;
  publicContent: typeof DEFAULT_PUBLIC_CONTENT;
}

function MarketingFrame({
  children,
  isDark,
  onToggleTheme,
  onOpenLogin,
  onOpenPayment,
  onOpenTransactions,
  onOpenDeleteAccount,
  publicContent,
}: MarketingFrameProps) {
  return (
    <div className="h-[100dvh] min-h-0 overflow-y-auto bg-[var(--bg-primary)]">
      <MarketingNav
        isDark={isDark}
        onToggleTheme={onToggleTheme}
        onOpenLogin={onOpenLogin}
        onOpenPayment={onOpenPayment}
        onOpenTransactions={onOpenTransactions}
        onOpenDeleteAccount={onOpenDeleteAccount}
      />
      {children}
      <Footer content={publicContent} />
    </div>
  );
}

interface ChatShellProps {
  isDark: boolean;
  sidebarOpen: boolean;
  onToggleTheme: () => void;
  onToggleSidebar: () => void;
  onOpenLogin: () => void;
  onOpenPayment: () => void;
  onOpenTransactions: () => void;
  onOpenDeleteAccount: () => void;
}

function ChatShell({
  isDark,
  sidebarOpen,
  onToggleTheme,
  onToggleSidebar,
  onOpenLogin,
  onOpenPayment,
  onOpenTransactions,
  onOpenDeleteAccount,
}: ChatShellProps) {
  return (
    <div className="flex h-[100dvh] min-h-0 w-full overflow-hidden bg-[var(--bg-primary)]">
      <div
        className={`
          h-full min-h-0 flex-shrink-0 transition-all duration-300 ease-in-out
          ${sidebarOpen ? 'w-[300px]' : 'w-0'}
          overflow-hidden
        `}
      >
        <Sidebar
          isDark={isDark}
          onToggleTheme={onToggleTheme}
          onOpenPayment={onOpenPayment}
          onOpenLogin={onOpenLogin}
          onOpenTransactions={onOpenTransactions}
          onOpenDeleteAccount={onOpenDeleteAccount}
        />
      </div>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex flex-none items-center border-b border-[var(--border-color)] bg-[var(--bg-secondary)]/80 px-4 py-2 backdrop-blur-lg">
          <button
            id="btn-toggle-sidebar"
            onClick={onToggleSidebar}
            className="cursor-pointer rounded-lg p-2 text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            title={sidebarOpen ? 'Ẩn sidebar' : 'Hiện sidebar'}
          >
            <HiOutlineBars3 className="h-5 w-5" />
          </button>
          <h2 className="ml-3 text-sm font-medium text-[var(--text-secondary)]">
            Chatbot Kinh Tế Việt Nam
          </h2>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--success)]" />
            <span className="text-xs text-[var(--text-muted)]">Online</span>
          </div>
        </div>

        <ChatPage onOpenLogin={onOpenLogin} />
      </div>
    </div>
  );
}


function RouteMeta() {
  const location = useLocation();
  useEffect(() => {
    const titles: Record<string, string> = {
      '/': 'Chatbot Kinh Tế Việt Nam - AI có nguồn và kiểm soát credit',
      '/about': 'Giới thiệu - Chatbot Kinh Tế Việt Nam',
      '/pricing': 'Bảng giá credit - Chatbot Kinh Tế Việt Nam',
      '/docs': 'Tài liệu - Chatbot Kinh Tế Việt Nam',
      '/security': 'Bảo mật - Chatbot Kinh Tế Việt Nam',
      '/terms': 'Điều khoản - Chatbot Kinh Tế Việt Nam',
      '/privacy': 'Quyền riêng tư - Chatbot Kinh Tế Việt Nam',
      '/support': 'Hỗ trợ - Chatbot Kinh Tế Việt Nam',
      '/chat': 'Chat - Chatbot Kinh Tế Việt Nam',
      '/admin': 'Admin - Chatbot Kinh Tế Việt Nam',
    };
    document.title = titles[location.pathname] || 'Chatbot Kinh Tế Việt Nam';
  }, [location.pathname]);
  return null;
}

function AppContent() {
  const { checkAuth } = useAuthStore();
  const [showLogin, setShowLogin] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [showTransactions, setShowTransactions] = useState(false);
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [publicContent, setPublicContent] = useState(DEFAULT_PUBLIC_CONTENT);

  const refreshPublicContent = useCallback(async () => {
    try {
      const response = await getPublicContent();
      if (response.data) {
        setPublicContent(response.data);
      }
    } catch {
      setPublicContent(DEFAULT_PUBLIC_CONTENT);
    }
  }, []);

  useEffect(() => {
    void refreshPublicContent();
  }, [refreshPublicContent]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.style.setProperty('--bg-primary', '#080b10');
      root.style.setProperty('--bg-secondary', '#10151d');
      root.style.setProperty('--bg-card', '#171d27');
      root.style.setProperty('--bg-hover', '#1f2835');
      root.style.setProperty('--border-color', '#253040');
      root.style.setProperty('--text-primary', '#f3f5f1');
      root.style.setProperty('--text-secondary', '#a8b0ad');
      root.style.setProperty('--text-muted', '#68736f');
    } else {
      root.style.setProperty('--bg-primary', '#f7f7f2');
      root.style.setProperty('--bg-secondary', '#ffffff');
      root.style.setProperty('--bg-card', '#eef1ec');
      root.style.setProperty('--bg-hover', '#e3e8e1');
      root.style.setProperty('--border-color', '#cfd8d1');
      root.style.setProperty('--text-primary', '#151917');
      root.style.setProperty('--text-secondary', '#4b5751');
      root.style.setProperty('--text-muted', '#7b867f');
    }
  }, [isDark]);

  const marketingProps = {
    isDark,
    onToggleTheme: () => setIsDark((value) => !value),
    onOpenLogin: () => setShowLogin(true),
    onOpenPayment: () => setShowPayment(true),
    onOpenTransactions: () => setShowTransactions(true),
    onOpenDeleteAccount: () => setShowDeleteAccount(true),
    publicContent,
  };

  return (
    <>
      <RouteMeta />
      <Routes>
        <Route
          path="/"
          element={
            <MarketingFrame {...marketingProps}>
              <HomePage onOpenPayment={() => setShowPayment(true)} />
            </MarketingFrame>
          }
        />
        <Route
          path="/about"
          element={
            <MarketingFrame {...marketingProps}>
              <AboutPage />
            </MarketingFrame>
          }
        />
        <Route
          path="/pricing"
          element={
            <MarketingFrame {...marketingProps}>
              <PricingPage onOpenPayment={() => setShowPayment(true)} />
            </MarketingFrame>
          }
        />
        {(['docs', 'security'] as const).map((type) => (
          <Route
            key={type}
            path={`/${type}`}
            element={
              <MarketingFrame {...marketingProps}>
                <InfoPage type={type} />
              </MarketingFrame>
            }
          />
        ))}
        {(['privacy', 'terms', 'support'] as const).map((type) => (
          <Route
            key={type}
            path={'/' + type}
            element={
              <MarketingFrame {...marketingProps}>
                <PublicContentPage type={type} content={publicContent} />
              </MarketingFrame>
            }
          />
        ))}
        <Route
          path="/admin"
          element={
            <MarketingFrame {...marketingProps}>
              <AdminPage onOpenLogin={() => setShowLogin(true)} onPublicContentUpdated={refreshPublicContent} />
            </MarketingFrame>
          }
        />
        <Route
          path="/chat"
          element={
            <ChatShell
              isDark={isDark}
              sidebarOpen={sidebarOpen}
              onToggleTheme={() => setIsDark((value) => !value)}
              onToggleSidebar={() => setSidebarOpen((value) => !value)}
              onOpenLogin={() => setShowLogin(true)}
              onOpenPayment={() => setShowPayment(true)}
              onOpenTransactions={() => setShowTransactions(true)}
              onOpenDeleteAccount={() => setShowDeleteAccount(true)}
            />
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <LoginModal isOpen={showLogin} onClose={() => setShowLogin(false)} />
      <PaymentModal isOpen={showPayment} onClose={() => setShowPayment(false)} />
      <TransactionHistoryModal isOpen={showTransactions} onClose={() => setShowTransactions(false)} />
      <DeleteAccountModal isOpen={showDeleteAccount} onClose={() => setShowDeleteAccount(false)} />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
