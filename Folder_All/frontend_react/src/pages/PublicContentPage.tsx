import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';
import { HiOutlineArrowRight, HiOutlineDocumentText, HiOutlineEnvelope, HiOutlineLifebuoy, HiOutlineShieldCheck } from 'react-icons/hi2';
import type { PublicContentData } from '../types';

interface PublicContentPageProps {
  type: 'privacy' | 'terms' | 'support';
  content: PublicContentData;
}

export default function PublicContentPage({ type, content }: PublicContentPageProps) {
  const page = content[type];
  const isPrivacy = type === 'privacy';
  const isSupport = type === 'support';
  const Icon = isPrivacy ? HiOutlineShieldCheck : isSupport ? HiOutlineLifebuoy : HiOutlineDocumentText;
  const supportEmail = content.support.email.trim();

  return (
    <main className="min-h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <section className="mx-auto w-full max-w-4xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
          <Icon className="h-6 w-6" />
        </div>
        <p className="mt-6 text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">
          {isPrivacy ? 'Quyền riêng tư và dữ liệu' : isSupport ? 'Trung tâm hỗ trợ' : 'Quy định sử dụng dịch vụ'}
        </p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight sm:text-5xl">{page.title}</h1>

        <article className="mt-10 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 sm:p-8">
          <div className="public-content text-sm leading-7 text-[var(--text-secondary)] sm:text-base">
            <ReactMarkdown>{page.content}</ReactMarkdown>
          </div>
        </article>

        {isSupport && supportEmail && (
          <a href={`mailto:${supportEmail}`} className="mt-6 inline-flex h-11 items-center gap-2 rounded-lg border border-emerald-500/35 bg-emerald-500/10 px-5 text-sm font-semibold text-emerald-300">
            <HiOutlineEnvelope className="h-4 w-4" />
            {supportEmail}
          </a>
        )}

        <Link to="/chat" className="mt-6 inline-flex h-11 items-center gap-2 rounded-lg bg-[var(--text-primary)] px-5 text-sm font-semibold text-[var(--bg-primary)]">
          Mở chatbot <HiOutlineArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </main>
  );
}
