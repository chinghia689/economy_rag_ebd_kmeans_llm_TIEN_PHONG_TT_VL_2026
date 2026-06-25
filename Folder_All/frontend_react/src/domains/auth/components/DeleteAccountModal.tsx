import { FormEvent, useEffect, useState } from 'react';
import { HiOutlineExclamationTriangle, HiOutlineTrash, HiOutlineXMark } from 'react-icons/hi2';
import { deleteMyAccount, getErrorMessage } from '../../../services/api';
import { useAuthStore } from '../authStore';

interface DeleteAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DeleteAccountModal({ isOpen, onClose }: DeleteAccountModalProps) {
  const { user, logout } = useAuthStore();
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setConfirmation('');
      setError('');
      setIsDeleting(false);
    }
  }, [isOpen]);

  if (!isOpen || !user) return null;

  const emailMatches = confirmation.trim().toLowerCase() === user.email.toLowerCase();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!emailMatches) return;
    setIsDeleting(true);
    setError('');
    try {
      await deleteMyAccount(confirmation);
      logout();
      onClose();
    } catch (err) {
      setError(getErrorMessage(err, 'Không thể xóa tài khoản.'));
      setIsDeleting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 p-4" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && !isDeleting && onClose()}>
      <section role="dialog" aria-modal="true" aria-labelledby="delete-account-title" className="w-full max-w-md rounded-xl border border-red-500/35 bg-[var(--bg-secondary)] p-6 text-[var(--text-primary)] shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/15 text-red-300">
            <HiOutlineExclamationTriangle className="h-6 w-6" />
          </div>
          <button type="button" onClick={onClose} disabled={isDeleting} className="rounded-lg p-2 text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] disabled:opacity-50" aria-label="Đóng">
            <HiOutlineXMark className="h-5 w-5" />
          </button>
        </div>

        <h2 id="delete-account-title" className="mt-4 text-xl font-semibold">Xóa tài khoản vĩnh viễn</h2>
        <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
          Toàn bộ hội thoại, credit và dữ liệu tài khoản sẽ bị xóa. Email <strong className="text-[var(--text-primary)]">{user.email}</strong> sẽ bị chặn và không thể đăng nhập lại.
        </p>

        {error && <div className="mt-4 rounded-lg border border-red-500/35 bg-red-500/10 p-3 text-sm text-red-200">{error}</div>}

        <form onSubmit={handleSubmit} className="mt-5">
          <label className="block text-sm text-[var(--text-secondary)]">
            Nhập email để xác nhận
            <input
              type="email"
              autoFocus
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              placeholder={user.email}
              className="mt-2 h-10 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-red-400"
            />
          </label>
          <div className="mt-5 flex justify-end gap-3">
            <button type="button" onClick={onClose} disabled={isDeleting} className="h-10 rounded-lg border border-[var(--border-color)] px-4 text-sm text-[var(--text-secondary)] disabled:opacity-50">Hủy</button>
            <button type="submit" disabled={!emailMatches || isDeleting} className="inline-flex h-10 items-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-45">
              <HiOutlineTrash className="h-4 w-4" />
              {isDeleting ? 'Đang xóa...' : 'Xóa vĩnh viễn'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
