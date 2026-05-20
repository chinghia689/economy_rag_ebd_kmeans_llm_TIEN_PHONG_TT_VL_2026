import { useState, useEffect } from 'react';
import Sidebar from './components/Layout/Sidebar';
import ChatPage from './domains/chat/pages/ChatPage';
import LoginModal from './domains/auth/components/LoginModal';
import PaymentModal from './domains/payment/components/PaymentModal';
import { useAuthStore } from './domains/auth/authStore';
import { HiOutlineBars3 } from 'react-icons/hi2';

export default function App() {
  const { checkAuth } = useAuthStore();
  const [showLogin, setShowLogin] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Check auth on mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Theme toggle — update CSS variables
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.style.setProperty('--bg-primary', '#0a0e1a');
      root.style.setProperty('--bg-secondary', '#111827');
      root.style.setProperty('--bg-card', '#1a1f35');
      root.style.setProperty('--bg-hover', '#242b45');
      root.style.setProperty('--border-color', '#1e2a4a');
      root.style.setProperty('--text-primary', '#e8ecf4');
      root.style.setProperty('--text-secondary', '#8892a8');
      root.style.setProperty('--text-muted', '#5a6478');
    } else {
      root.style.setProperty('--bg-primary', '#f8fafc');
      root.style.setProperty('--bg-secondary', '#ffffff');
      root.style.setProperty('--bg-card', '#f1f5f9');
      root.style.setProperty('--bg-hover', '#e2e8f0');
      root.style.setProperty('--border-color', '#cbd5e1');
      root.style.setProperty('--text-primary', '#1e293b');
      root.style.setProperty('--text-secondary', '#475569');
      root.style.setProperty('--text-muted', '#94a3b8');
    }
  }, [isDark]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-primary)]">
      {/* ── Sidebar ── */}
      <div
        className={`
          flex-shrink-0 transition-all duration-300 ease-in-out
          ${sidebarOpen ? 'w-[300px]' : 'w-0'}
          overflow-hidden
        `}
      >
        <Sidebar
          isDark={isDark}
          onToggleTheme={() => setIsDark(!isDark)}
          onOpenPayment={() => setShowPayment(true)}
          onOpenLogin={() => setShowLogin(true)}
        />
      </div>

      {/* ── Main Area ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toggle sidebar button */}
        <div className="flex items-center px-4 py-2 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]/80 backdrop-blur-lg">
          <button
            id="btn-toggle-sidebar"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-xl text-[var(--text-secondary)] hover:text-[var(--text-primary)]
                       hover:bg-[var(--bg-hover)] transition-all cursor-pointer"
            title={sidebarOpen ? 'Ẩn sidebar' : 'Hiện sidebar'}
          >
            <HiOutlineBars3 className="w-5 h-5" />
          </button>
          <h2 className="ml-3 text-sm font-medium text-[var(--text-secondary)]">
            Chatbot Kinh Tế Việt Nam
          </h2>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
            <span className="text-xs text-[var(--text-muted)]">Online</span>
          </div>
        </div>

        {/* Chat page */}
        <ChatPage />
      </div>

      {/* ── Modals ── */}
      <LoginModal isOpen={showLogin} onClose={() => setShowLogin(false)} />
      <PaymentModal isOpen={showPayment} onClose={() => setShowPayment(false)} />
    </div>
  );
}
