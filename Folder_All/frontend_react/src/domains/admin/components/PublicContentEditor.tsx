import { FormEvent } from 'react';
import { HiOutlineDocumentText } from 'react-icons/hi2';

interface PublicContentEditorProps {
  values: Record<string, string>;
  isSaving: boolean;
  onChange: (key: string, value: string) => void;
  onSave: () => void;
}

const inputClass = 'mt-2 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]';

export default function PublicContentEditor({ values, isSaving, onChange, onSave }: PublicContentEditorProps) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSave();
  }

  return (
    <section className="mt-8 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]">
      <div className="border-b border-[var(--border-color)] p-4">
        <div className="flex items-center gap-2">
          <HiOutlineDocumentText className="h-5 w-5 text-[var(--text-secondary)]" />
          <h2 className="text-lg font-semibold">Nội dung chính sách và hỗ trợ</h2>
        </div>
        <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
          Nội dung này hiển thị ở footer và các trang công khai. Có thể dùng Markdown cho tiêu đề phụ và danh sách.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-6 p-4 xl:grid-cols-3">
        <div className="space-y-4">
          <label className="block text-sm text-[var(--text-secondary)]">
            Tiêu đề chính sách bảo mật
            <input
              required
              value={values.PUBLIC_PRIVACY_TITLE ?? ''}
              onChange={(event) => onChange('PUBLIC_PRIVACY_TITLE', event.target.value)}
              className={`${inputClass} h-10`}
            />
          </label>
          <label className="block text-sm text-[var(--text-secondary)]">
            Nội dung chính sách bảo mật
            <textarea
              required
              rows={13}
              value={values.PUBLIC_PRIVACY_CONTENT ?? ''}
              onChange={(event) => onChange('PUBLIC_PRIVACY_CONTENT', event.target.value)}
              className={`${inputClass} resize-y py-3 leading-6`}
            />
          </label>
        </div>

        <div className="space-y-4">
          <label className="block text-sm text-[var(--text-secondary)]">
            Tiêu đề điều khoản sử dụng
            <input
              required
              value={values.PUBLIC_TERMS_TITLE ?? ''}
              onChange={(event) => onChange('PUBLIC_TERMS_TITLE', event.target.value)}
              className={`${inputClass} h-10`}
            />
          </label>
          <label className="block text-sm text-[var(--text-secondary)]">
            Nội dung điều khoản sử dụng
            <textarea
              required
              rows={13}
              value={values.PUBLIC_TERMS_CONTENT ?? ''}
              onChange={(event) => onChange('PUBLIC_TERMS_CONTENT', event.target.value)}
              className={`${inputClass} resize-y py-3 leading-6`}
            />
          </label>
        </div>

        <div className="space-y-4">
          <label className="block text-sm text-[var(--text-secondary)]">
            Tiêu đề hỗ trợ
            <input
              required
              value={values.PUBLIC_SUPPORT_TITLE ?? ''}
              onChange={(event) => onChange('PUBLIC_SUPPORT_TITLE', event.target.value)}
              className={`${inputClass} h-10`}
            />
          </label>
          <label className="block text-sm text-[var(--text-secondary)]">
            Email hỗ trợ (không bắt buộc)
            <input
              type="email"
              value={values.PUBLIC_SUPPORT_EMAIL ?? ''}
              onChange={(event) => onChange('PUBLIC_SUPPORT_EMAIL', event.target.value)}
              placeholder="hotro@example.com"
              className={`${inputClass} h-10`}
            />
          </label>
          <label className="block text-sm text-[var(--text-secondary)]">
            Nội dung hỗ trợ
            <textarea
              required
              rows={9}
              value={values.PUBLIC_SUPPORT_CONTENT ?? ''}
              onChange={(event) => onChange('PUBLIC_SUPPORT_CONTENT', event.target.value)}
              className={`${inputClass} resize-y py-3 leading-6`}
            />
          </label>
        </div>

        <div className="flex items-center justify-end border-t border-[var(--border-color)] pt-4 xl:col-span-3">
          <button
            type="submit"
            disabled={isSaving}
            className="h-10 rounded-lg bg-[var(--text-primary)] px-5 text-sm font-semibold text-[var(--bg-primary)] transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSaving ? 'Đang lưu...' : 'Lưu nội dung công khai'}
          </button>
        </div>
      </form>
    </section>
  );
}
