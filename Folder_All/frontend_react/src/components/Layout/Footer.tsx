import { Link } from 'react-router-dom';
import { HiOutlineEnvelope, HiOutlineShieldCheck } from 'react-icons/hi2';
import type { PublicContentData } from '../../types';

interface FooterProps {
  content: PublicContentData;
}

export default function Footer({ content }: FooterProps) {
  const supportEmail = content.support.email.trim();

  return (
    <footer className="border-t border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-primary)]">
      <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1.2fr_0.8fr_1fr] lg:px-8">
        <div>
          <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-xs font-bold">
              KT
            </span>
            Chatbot Kinh Tế
          </Link>
          <p className="mt-4 max-w-sm text-sm leading-6 text-[var(--text-secondary)]">
            Trợ lý nghiên cứu kinh tế Việt Nam có nguồn, lịch sử hội thoại và kiểm soát credit.
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">Thông tin</p>
          <nav className="mt-4 flex flex-col items-start gap-3 text-sm text-[var(--text-secondary)]">
            <Link to="/privacy" className="transition-colors hover:text-[var(--text-primary)]">{content.privacy.title}</Link>
            <Link to="/support" className="transition-colors hover:text-[var(--text-primary)]">{content.support.title}</Link>
            <Link to="/terms" className="transition-colors hover:text-[var(--text-primary)]">{content.terms.title}</Link>
          </nav>
        </div>

        <div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <HiOutlineShieldCheck className="h-5 w-5 text-emerald-300" />
            Bảo mật và hỗ trợ
          </div>
          <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
            Xem chính sách dữ liệu hoặc gửi yêu cầu hỗ trợ khi gặp vấn đề với tài khoản, credit và thanh toán.
          </p>
          {supportEmail && (
            <a href={`mailto:${supportEmail}`} className="mt-4 inline-flex items-center gap-2 text-sm text-emerald-300 hover:text-emerald-200">
              <HiOutlineEnvelope className="h-4 w-4" />
              {supportEmail}
            </a>
          )}
        </div>
      </div>
      <div className="border-t border-[var(--border-color)] px-4 py-4 text-center text-xs text-[var(--text-muted)]">
        © {new Date().getFullYear()} Chatbot Kinh Tế Việt Nam
      </div>
    </footer>
  );
}
