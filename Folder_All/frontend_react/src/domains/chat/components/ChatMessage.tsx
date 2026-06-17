import { useState } from 'react';
import {
  HiOutlineArrowDownTray,
  HiOutlineArrowPath,
  HiOutlineBookmark,
  HiOutlineCheck,
  HiOutlineClipboardDocument,
  HiOutlineClock,
  HiOutlineDocumentText,
  HiOutlineSparkles,
  HiOutlineUserCircle,
} from 'react-icons/hi2';
import type { Message } from '../../../types';

interface ChatMessageProps {
  message: Message;
  isLatest?: boolean;
  onRegenerate?: () => void;
}

export default function ChatMessage({ message, isLatest, onRegenerate }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied] = useState(false);


  function handleExport() {
    const filename = `answer-${new Date(message.timestamp).toISOString().slice(0, 10)}.md`;
    const sources = (message.sources || [])
      .map((src, index) => `${index + 1}. ${src.source || 'Không rõ nguồn'}\n${src.content}`)
      .join('\n\n');
    const body = `# Câu trả lời\n\n${message.content}\n\n${sources ? `## Nguồn\n\n${sources}\n` : ''}`;
    const blob = new Blob([body], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handleSaveAnswer() {
    const saved = JSON.parse(localStorage.getItem('saved_answers') || '[]');
    saved.unshift({ ...message, savedAt: Date.now() });
    localStorage.setItem('saved_answers', JSON.stringify(saved.slice(0, 100)));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  async function handleCopy() {
    await navigator.clipboard?.writeText(message.content).catch(() => undefined);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} ${
        isLatest ? (isUser ? 'animate-slide-in-right' : 'animate-slide-in-left') : ''
      }`}
    >
      <div className={`max-w-[88%] sm:max-w-[78%] ${isUser ? 'order-2' : 'order-1'}`}>
        <div className={`mb-2 flex items-center gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {!isUser && (
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-emerald-500/25 bg-emerald-500/12 text-emerald-200">
              <HiOutlineSparkles className="h-4 w-4" />
            </div>
          )}
          <span className="text-xs font-medium text-[var(--text-muted)]">
            {isUser ? 'Bạn' : 'Chatbot Kinh Tế'}
          </span>
          {isUser && (
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-sky-500/25 bg-sky-500/12 text-sky-200">
              <HiOutlineUserCircle className="h-4 w-4" />
            </div>
          )}
        </div>

        <div
          className={`border px-4 py-3 text-sm leading-7 text-[var(--text-primary)] shadow-sm ${
            isUser
              ? 'rounded-lg rounded-tr-sm border-sky-500/28 bg-sky-500/10'
              : 'rounded-lg rounded-tl-sm border-[var(--border-color)] bg-[var(--bg-card)]'
          }`}
        >
          <div className="whitespace-pre-wrap break-words">{message.content}</div>
        </div>

        <div className={`mt-2 flex flex-wrap items-center gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {!isUser && message.responseTime !== undefined && (
            <span className="inline-flex h-7 items-center gap-1 rounded-lg border border-[var(--border-color)] px-2 text-xs text-[var(--text-muted)]">
              <HiOutlineClock className="h-3.5 w-3.5" />
              {message.responseTime}s
            </span>
          )}
          {!isUser && message.tokenUsed !== undefined && (
            <span className="inline-flex h-7 items-center rounded-lg border border-[var(--border-color)] px-2 text-xs text-[var(--text-muted)]">
              {message.tokenUsed.toLocaleString('vi-VN')} credit
            </span>
          )}
          {!isUser && message.sources && message.sources.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              className="inline-flex h-7 items-center gap-1 rounded-lg border border-emerald-500/25 px-2 text-xs text-emerald-300 transition-colors hover:bg-emerald-500/10"
            >
              <HiOutlineDocumentText className="h-3.5 w-3.5" />
              {showSources ? 'Ẩn nguồn' : `${message.sources.length} nguồn`}
            </button>
          )}
          <button
            onClick={() => void handleCopy()}
            className="inline-flex h-7 items-center gap-1 rounded-lg border border-[var(--border-color)] px-2 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            {copied ? <HiOutlineCheck className="h-3.5 w-3.5" /> : <HiOutlineClipboardDocument className="h-3.5 w-3.5" />}
            {copied ? 'Đã lưu' : 'Copy'}
          </button>
          {!isUser && (
            <>
              <button
                onClick={handleSaveAnswer}
                className="inline-flex h-7 items-center gap-1 rounded-lg border border-[var(--border-color)] px-2 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <HiOutlineBookmark className="h-3.5 w-3.5" />
                Save
              </button>
              <button
                onClick={handleExport}
                className="inline-flex h-7 items-center gap-1 rounded-lg border border-[var(--border-color)] px-2 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <HiOutlineArrowDownTray className="h-3.5 w-3.5" />
                Export
              </button>
              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className="inline-flex h-7 items-center gap-1 rounded-lg border border-[var(--border-color)] px-2 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <HiOutlineArrowPath className="h-3.5 w-3.5" />
                  Regenerate
                </button>
              )}
            </>
          )}
        </div>

        {showSources && message.sources && (
          <div className="mt-3 space-y-2 animate-fade-in">
            {message.sources.map((src, i) => (
              <article
                key={`${src.source}-${i}`}
                className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-3 text-xs leading-6 text-[var(--text-secondary)]"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="truncate font-semibold text-emerald-300">
                    Nguồn {i + 1}: {src.source?.split('/').pop() || 'Không rõ'}
                  </span>
                  <span className="shrink-0 text-[10px] text-[var(--text-muted)]">{src.score || src.relevance_score ? `Score ${Number(src.score || src.relevance_score).toFixed(2)}` : 'RAG'}</span>
                </div>
                <p className="line-clamp-5">{src.content}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
