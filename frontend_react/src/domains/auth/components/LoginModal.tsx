import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../authStore';
import { createLoginSession, pollLoginSession, getGoogleLoginUrl, getErrorMessage } from '../../../services/api';
import { HiOutlineXMark } from 'react-icons/hi2';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function generateSessionId(): string {
  return 'sess_' + Date.now().toString(36) + Math.random().toString(36).substring(2, 10);
}

export default function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const { login } = useAuthStore();
  const [status, setStatus] = useState<'idle' | 'waiting' | 'success' | 'error'>('idle');
  const [error, setError] = useState('');
  const [loginUrl, setLoginUrl] = useState('');
  const [popupBlocked, setPopupBlocked] = useState(false);
  const pollingRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const statusRef = useRef(status);
  const sessionIdRef = useRef('');

  const clearTimers = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const resetLoginState = useCallback(() => {
    clearTimers();
    sessionIdRef.current = '';
    setStatus('idle');
    setError('');
    setLoginUrl('');
    setPopupBlocked(false);
  }, [clearTimers]);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  useEffect(() => {
    if (isOpen) {
      resetLoginState();
    } else {
      clearTimers();
    }
  }, [isOpen, resetLoginState, clearTimers]);

  const handleGoogleLogin = async () => {
    try {
      clearTimers();
      setStatus('waiting');
      setError('');
      setPopupBlocked(false);

      const sessionId = generateSessionId();
      sessionIdRef.current = sessionId;

      // 1. Tạo phiên chờ
      await createLoginSession(sessionId);

      // 2. Mở tab Google OAuth
      const nextLoginUrl = getGoogleLoginUrl(sessionId);
      setLoginUrl(nextLoginUrl);
      const popup = window.open(nextLoginUrl, '_blank', 'width=500,height=600');
      if (!popup) {
        setPopupBlocked(true);
      }

      // 3. Polling kiểm tra
      pollingRef.current = window.setInterval(async () => {
        try {
          const res = await pollLoginSession(sessionId);

          if (res?.status === 'completed' && res.token && res.user) {
            clearTimers();
            setStatus('success');

            await login(res.token, res.user);

            timeoutRef.current = window.setTimeout(onClose, 1000);
          }
        } catch {
          // Ignore polling errors, keep retrying
        }
      }, 2000);

      // Timeout sau 5 phút
      timeoutRef.current = window.setTimeout(() => {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
          if (statusRef.current === 'waiting') {
            setStatus('error');
            setError('Hết thời gian chờ đăng nhập. Vui lòng thử lại.');
          }
        }
      }, 300000);
    } catch (err: unknown) {
      clearTimers();
      setStatus('error');
      setError(getErrorMessage(err, 'Lỗi tạo phiên đăng nhập.'));
    }
  };

  const handleClose = () => {
    resetLoginState();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md mx-4 p-8 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)]
                      shadow-2xl animate-fade-in-up">
        {/* Close */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[var(--text-muted)]
                     hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all cursor-pointer"
        >
          <HiOutlineXMark className="w-5 h-5" />
        </button>

        {/* Content */}
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-[#667eea] to-[#764ba2]
                          flex items-center justify-center shadow-lg">
            <span className="text-2xl">🔐</span>
          </div>

          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">Đăng nhập</h2>
          <p className="text-sm text-[var(--text-secondary)] mb-6">
            Đăng nhập để lưu lịch sử chat và nạp token
          </p>

          {status === 'idle' && (
            <button
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-3 px-6 py-3 rounded-xl
                         bg-white text-gray-700 font-medium text-sm
                         hover:bg-gray-50 transition-all shadow-md cursor-pointer"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Đăng nhập với Google
            </button>
          )}

          {status === 'waiting' && (
            <div className="py-4">
              <div className="w-10 h-10 mx-auto mb-4 border-2 border-[var(--accent-primary)] border-t-transparent
                              rounded-full animate-spin" />
              <p className="text-sm text-[var(--text-secondary)]">
                Đang chờ đăng nhập Google...<br />
                <span className="text-xs text-[var(--text-muted)]">
                  Vui lòng hoàn tất trong tab mới
                </span>
              </p>
              {popupBlocked && loginUrl && (
                <button
                  onClick={() => window.open(loginUrl, '_blank', 'width=500,height=600')}
                  className="mt-4 px-5 py-2 rounded-xl bg-[var(--bg-hover)] text-[var(--text-primary)]
                             text-sm hover:bg-[var(--border-color)] transition-all cursor-pointer"
                >
                  Mở lại đăng nhập
                </button>
              )}
            </div>
          )}

          {status === 'success' && (
            <div className="py-4">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[var(--success)]/20
                              flex items-center justify-center">
                <span className="text-2xl">✅</span>
              </div>
              <p className="text-sm text-[var(--success)] font-medium">Đăng nhập thành công!</p>
            </div>
          )}

          {status === 'error' && (
            <div className="py-4">
              <p className="text-sm text-[var(--danger)] mb-4">{error}</p>
              <button
                onClick={resetLoginState}
                className="px-6 py-2 rounded-xl bg-[var(--bg-hover)] text-[var(--text-primary)]
                           text-sm hover:bg-[var(--border-color)] transition-all cursor-pointer"
              >
                Thử lại
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
