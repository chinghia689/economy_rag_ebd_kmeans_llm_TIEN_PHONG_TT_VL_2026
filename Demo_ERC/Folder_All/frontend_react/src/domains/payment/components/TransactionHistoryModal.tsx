import { useRef } from 'react';
import {
  HiOutlineArrowDownTray,
  HiOutlineArrowPath,
  HiOutlineArrowUpTray,
  HiOutlineBanknotes,
  HiOutlineCircleStack,
  HiOutlineClock,
  HiOutlineXMark,
} from 'react-icons/hi2';
import { useAuthStore } from '../../auth/authStore';
import { useFocusTrap } from '../../../hooks/useFocusTrap';

interface TransactionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function formatDate(value: string) {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('vi-VN');
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('vi-VN').format(value || 0);
}

function formatReason(reason: string, relatedPaymentId?: number | null) {
  if (reason === 'payment') {
    return relatedPaymentId ? `Thanh toán SePay #${relatedPaymentId}` : 'Thanh toán SePay';
  }
  if (reason.startsWith('admin_topup:')) {
    const parts = reason.split(':');
    const note = parts.slice(2).join(':');
    return note ? `Admin nạp credit · ${note}` : 'Admin nạp credit';
  }
  if (reason.startsWith('chat:')) return 'Sử dụng chatbot';
  if (reason.startsWith('async_chat:')) return 'Sử dụng chatbot';
  return reason || 'Giao dịch credit';
}

export default function TransactionHistoryModal({ isOpen, onClose }: TransactionHistoryModalProps) {
  const { tokenTransactions, tokenBalance, refreshBalance } = useAuthStore();
  const modalRef = useRef<HTMLDivElement | null>(null);

  useFocusTrap(isOpen, modalRef, onClose);

  if (!isOpen) return null;

  const totalCredit = tokenTransactions.filter((tx) => tx.delta > 0).reduce((sum, tx) => sum + tx.delta, 0);
  const totalDebit = tokenTransactions.filter((tx) => tx.delta < 0).reduce((sum, tx) => sum + Math.abs(tx.delta), 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-6 backdrop-blur-sm animate-fade-in">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="transaction-history-title"
        tabIndex={-1}
        className="relative flex max-h-[90dvh] w-full max-w-3xl flex-col rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] shadow-2xl animate-fade-in-up"
      >
        <div className="flex flex-none items-start justify-between border-b border-[var(--border-color)] p-5">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.16em] text-[var(--text-muted)]">Credit ledger</p>
            <h2 id="transaction-history-title" className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">Lịch sử giao dịch</h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Số dư hiện tại: <span className="font-semibold text-[var(--text-primary)]">{formatNumber(tokenBalance ?? 0)}</span> credit
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            title="Đóng"
          >
            <HiOutlineXMark className="h-5 w-5" />
          </button>
        </div>

        <div className="grid flex-none gap-3 border-b border-[var(--border-color)] p-5 sm:grid-cols-3">
          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
            <HiOutlineCircleStack className="h-5 w-5 text-sky-300" />
            <p className="mt-3 text-xs text-[var(--text-muted)]">Số dư</p>
            <p className="mt-1 text-xl font-semibold">{formatNumber(tokenBalance ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
            <HiOutlineArrowDownTray className="h-5 w-5 text-emerald-300" />
            <p className="mt-3 text-xs text-[var(--text-muted)]">Tổng nạp gần đây</p>
            <p className="mt-1 text-xl font-semibold text-emerald-300">+{formatNumber(totalCredit)}</p>
          </div>
          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
            <HiOutlineArrowUpTray className="h-5 w-5 text-rose-300" />
            <p className="mt-3 text-xs text-[var(--text-muted)]">Tổng sử dụng gần đây</p>
            <p className="mt-1 text-xl font-semibold text-rose-300">-{formatNumber(totalDebit)}</p>
          </div>
        </div>

        <div className="flex flex-none items-center justify-between border-b border-[var(--border-color)] px-5 py-3">
          <p className="text-xs text-[var(--text-muted)]">{formatNumber(tokenTransactions.length)} giao dịch gần nhất</p>
          <button
            onClick={() => void refreshBalance()}
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <HiOutlineArrowPath className="h-4 w-4" />
            Làm mới
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {tokenTransactions.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[var(--border-color)] py-12 text-center">
              <HiOutlineCircleStack className="h-8 w-8 text-[var(--text-muted)]" />
              <p className="mt-3 text-sm font-medium text-[var(--text-primary)]">Chưa có giao dịch</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">Các lần nạp và sử dụng credit sẽ xuất hiện tại đây.</p>
            </div>
          ) : (
            <div className="relative space-y-3">
              {tokenTransactions.map((tx) => {
                const isCredit = tx.delta > 0;
                return (
                  <article
                    key={tx.id}
                    className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4"
                  >
                    <div className="flex items-start gap-4">
                      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${
                        isCredit ? 'border-emerald-500/30 bg-emerald-500/12 text-emerald-300' : 'border-rose-500/30 bg-rose-500/12 text-rose-300'
                      }`}>
                        {isCredit ? <HiOutlineBanknotes className="h-5 w-5" /> : <HiOutlineCircleStack className="h-5 w-5" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
                              {formatReason(tx.reason, tx.related_payment_id)}
                            </p>
                            <p className="mt-1 flex items-center gap-1 text-xs text-[var(--text-muted)]">
                              <HiOutlineClock className="h-3.5 w-3.5" />
                              {formatDate(tx.created_at)}
                            </p>
                          </div>
                          <div className={`shrink-0 text-right text-base font-bold ${isCredit ? 'text-emerald-300' : 'text-rose-300'}`}>
                            {isCredit ? '+' : ''}{formatNumber(tx.delta)}
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
                          <span className="rounded-lg bg-[var(--bg-primary)] px-2 py-1">TX #{tx.id}</span>
                          {tx.related_payment_id && <span className="rounded-lg bg-[var(--bg-primary)] px-2 py-1">Payment #{tx.related_payment_id}</span>}
                          <span className="rounded-lg bg-[var(--bg-primary)] px-2 py-1">{isCredit ? 'Credit' : 'Debit'}</span>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
