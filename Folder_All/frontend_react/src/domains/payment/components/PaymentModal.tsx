import { useState, useEffect, useRef, useCallback } from 'react';
import { createPayment, checkPaymentStatus, getErrorMessage } from '../../../services/api';
import { HiOutlineXMark, HiOutlineClipboardDocument, HiOutlineClock, HiOutlineCheckCircle, HiOutlineExclamationTriangle } from 'react-icons/hi2';
import { useFocusTrap } from '../../../hooks/useFocusTrap';
import type { PaymentCreateData } from '../../../types';
import { useAuthStore } from '../../auth/authStore';

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const packages = [
  { id: 'basic', name: 'Starter', tokens: 100, amount: 30000, badge: 'S' },
  { id: 'pro', name: 'Research', tokens: 500, amount: 120000, badge: 'R' },
  { id: 'premium', name: 'Team', tokens: 1200, amount: 250000, badge: 'T' },
];

export default function PaymentModal({ isOpen, onClose }: PaymentModalProps) {
  const { refreshBalance } = useAuthStore();
  const [step, setStep] = useState<'select' | 'transfer' | 'checking' | 'done'>('select');
  const [selectedPkg, setSelectedPkg] = useState(packages[0]);
  const [paymentData, setPaymentData] = useState<PaymentCreateData | null>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const pollingRef = useRef<number | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(timer);
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleCreatePayment = async () => {
    try {
      setError('');
      const res = await createPayment(selectedPkg.id);
      if (res.success && res.data) {
        const expiresAtMs = res.data.expires_at
          ? Date.parse(res.data.expires_at)
          : Date.now() + (res.data.expires_in_seconds || 300) * 1000;
        setPaymentData(res.data);
        setExpiresAt(Number.isNaN(expiresAtMs) ? Date.now() + 5 * 60 * 1000 : expiresAtMs);
        setStep('transfer');
      } else {
        setError(res.message || 'Lỗi tạo giao dịch.');
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Lỗi kết nối.'));
    }
  };

  const handleStartChecking = () => {
    if (!paymentData) return;

    setStep('checking');
    const paymentId = paymentData.payment_id;

    pollingRef.current = window.setInterval(async () => {
      try {
        const res = await checkPaymentStatus(paymentId);
        if (res.success && res.data?.status === 'completed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          void refreshBalance();
          setStep('done');
        } else if (res.success && res.data?.status === 'expired') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setPaymentData(null);
          setExpiresAt(null);
          setStep('select');
          setError('Giao dịch đã quá 5 phút và đã bị xóa. Vui lòng tạo giao dịch mới.');
        } else if (res.success && res.data?.expires_at) {
          const nextExpiresAt = Date.parse(res.data.expires_at);
          if (!Number.isNaN(nextExpiresAt)) setExpiresAt(nextExpiresAt);
        }
      } catch {
        // keep polling
      }
    }, 3000);

    // Timeout 5 phút
    setTimeout(() => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }, 300000);
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleClose = useCallback(() => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    setStep('select');
    setPaymentData(null);
    setExpiresAt(null);
    setError('');
    onClose();
  }, [onClose]);

  useFocusTrap(isOpen, modalRef, handleClose);

  useEffect(() => {
    if (!expiresAt || (step !== 'transfer' && step !== 'checking')) return;
    if (now < expiresAt) return;

    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (paymentData?.payment_id) {
      void checkPaymentStatus(paymentData.payment_id).catch(() => undefined);
    }
    setPaymentData(null);
    setExpiresAt(null);
    setStep('select');
    setError('Giao dịch đã quá 5 phút và đã bị xóa. Vui lòng tạo giao dịch mới.');
  }, [expiresAt, now, paymentData?.payment_id, step]);

  if (!isOpen) return null;

  const secondsLeft = Math.max(0, Math.floor(((expiresAt || Date.now()) - now) / 1000));
  const minutesLeft = Math.floor(secondsLeft / 60);
  const secondsRemainder = String(secondsLeft % 60).padStart(2, '0');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="payment-title"
        tabIndex={-1}
        className="relative w-full max-w-lg mx-4 p-8 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)]
                      shadow-2xl animate-fade-in-up max-h-[90vh] overflow-y-auto"
      >
        {/* Close */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[var(--text-muted)]
                     hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all cursor-pointer"
        >
          <HiOutlineXMark className="w-5 h-5" />
        </button>

        <h2 id="payment-title" className="text-xl font-bold text-[var(--text-primary)] mb-1">Nạp credit</h2>
        <p className="text-sm text-[var(--text-secondary)] mb-6">Chọn gói, quét QR và theo dõi trạng thái thanh toán realtime trong 5 phút.</p>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-[var(--danger)]/10 border border-[var(--danger)]/30
                          text-sm text-[var(--danger)]">
            {error}
          </div>
        )}

        {/* Step 1: Select package */}
        {step === 'select' && (
          <div className="space-y-4">
            <div className="grid gap-3">
              {packages.map((pkg) => (
                <button
                  key={pkg.id}
                  onClick={() => setSelectedPkg(pkg)}
                  className={`
                    flex items-center gap-4 p-4 rounded-xl border transition-all cursor-pointer text-left
                    ${selectedPkg.id === pkg.id
                      ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
                      : 'border-[var(--border-color)] bg-[var(--bg-secondary)] hover:border-[var(--border-hover)]'
                    }
                  `}
                >
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-sm font-bold text-[var(--text-primary)]">{pkg.badge}</span>
                  <div className="flex-1">
                    <p className="font-semibold text-sm text-[var(--text-primary)]">{pkg.name}</p>
                    <p className="text-xs text-[var(--text-secondary)]">{pkg.tokens.toLocaleString('vi-VN')} câu hỏi</p>
                  </div>
                  <p className="font-bold text-[var(--accent-primary)]">
                    {pkg.amount.toLocaleString('vi-VN')}đ
                  </p>
                </button>
              ))}
            </div>

            <button
              onClick={handleCreatePayment}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-[#667eea] to-[#764ba2]
                         text-white font-medium text-sm hover:opacity-90 transition-opacity cursor-pointer"
            >
              Tiếp tục
            </button>
          </div>
        )}

        {/* Step 2: Transfer info */}
        {step === 'transfer' && paymentData && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2 text-xs">
              {['Đang chờ', 'Đã nhận tiền', 'Đã cộng credit'].map((label, index) => (
                <div key={label} className={`rounded-lg border px-2 py-2 text-center ${index === 0 ? 'border-amber-500/35 bg-amber-500/10 text-amber-200' : 'border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-muted)]'}`}>{label}</div>
              ))}
            </div>

            <div className="flex items-center justify-center gap-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm text-[var(--text-secondary)]">
              <HiOutlineClock className="h-4 w-4 text-amber-300" />
              Hết hạn sau {minutesLeft}:{secondsRemainder}
            </div>

            {/* QR Code */}
            <div className="flex flex-col items-center">
              <img
                src={paymentData.qr_url}
                alt="QR chuyển khoản"
                className="w-56 h-56 rounded-xl border border-[var(--border-color)] bg-white object-contain"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = 'none';
                  (e.currentTarget.nextElementSibling as HTMLElement | null)?.removeAttribute('hidden');
                }}
              />
              <p hidden className="text-xs text-[var(--text-muted)] mt-2">Không tải được QR — dùng thông tin bên dưới</p>
              <p className="text-xs text-[var(--text-muted)] mt-2">Quét bằng app ngân hàng để điền tự động</p>
            </div>

            {/* Bank info */}
            <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">Ngân hàng:</span>
                <span className="font-medium text-[var(--text-primary)]">{paymentData.bank_name}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[var(--text-secondary)]">Số tài khoản:</span>
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-semibold text-[var(--text-primary)]">{paymentData.bank_account}</span>
                  <button
                    onClick={() => handleCopy(paymentData.bank_account, 'account')}
                    className="p-1 rounded hover:bg-[var(--bg-hover)] transition-all cursor-pointer
                               text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    title="Sao chép số tài khoản"
                  >
                    <HiOutlineClipboardDocument className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              {copied === 'account' && <p className="text-xs text-[var(--success)] -mt-1">Đã sao chép số tài khoản</p>}

              {paymentData.account_name && (
                <div className="flex justify-between">
                  <span className="text-[var(--text-secondary)]">Tên tài khoản:</span>
                  <span className="font-medium text-[var(--text-primary)] uppercase">{paymentData.account_name}</span>
                </div>
              )}

              <div className="flex justify-between">
                <span className="text-[var(--text-secondary)]">Số tiền:</span>
                <span className="font-bold text-[var(--accent-primary)]">
                  {paymentData.amount.toLocaleString('vi-VN')}đ
                </span>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[var(--text-secondary)]">Nội dung CK:</span>
                  <button
                    onClick={() => handleCopy(paymentData.transfer_content, 'content')}
                    className="p-1 rounded hover:bg-[var(--bg-hover)] transition-all cursor-pointer
                               text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    title="Sao chép nội dung"
                  >
                    <HiOutlineClipboardDocument className="w-3.5 h-3.5" />
                  </button>
                </div>
                <code className="block w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)]
                                 text-[var(--warning)] font-mono text-xs border border-[var(--border-color)] break-all">
                  {paymentData.transfer_content}
                </code>
                {copied === 'content' && <p className="text-xs text-[var(--success)] mt-1">Đã sao chép nội dung</p>}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[var(--warning)]/10 border border-[var(--warning)]/20 text-xs text-[var(--warning)]">
              <span className="inline-flex items-start gap-2"><HiOutlineExclamationTriangle className="mt-0.5 h-4 w-4 shrink-0" />Chuyển khoản đúng số tiền và nội dung - hệ thống tự xác nhận</span>
            </div>

            <button
              onClick={handleStartChecking}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-[#34d399] to-[#059669]
                         text-white font-medium text-sm hover:opacity-90 transition-opacity cursor-pointer"
            >
              Tôi đã chuyển khoản
            </button>
          </div>
        )}

        {/* Step 3: Checking */}
        {step === 'checking' && (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-4 border-2 border-[var(--accent-primary)] border-t-transparent
                            rounded-full animate-spin" />
            <p className="text-sm text-[var(--text-secondary)]">Đang chờ SePay xác nhận giao dịch...</p>
            <p className="text-xs text-[var(--text-muted)] mt-2">Hệ thống sẽ tự động xác nhận khi nhận được tiền</p>
          </div>
        )}

        {/* Step 4: Done */}
        {step === 'done' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--success)]/20
                            flex items-center justify-center">
              <HiOutlineCheckCircle className="h-8 w-8 text-[var(--success)]" />
            </div>
            <h3 className="text-lg font-bold text-[var(--success)] mb-2">Nạp thành công!</h3>
            <p className="text-sm text-[var(--text-secondary)] mb-6">
              Bạn đã nạp thành công {selectedPkg.tokens} credit hỏi
            </p>
            <button
              onClick={handleClose}
              className="px-8 py-2.5 rounded-xl bg-[var(--bg-hover)] text-[var(--text-primary)]
                         text-sm hover:bg-[var(--border-color)] transition-all cursor-pointer"
            >
              Đóng
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
