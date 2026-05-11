import type { Message } from '../../../types';
import { HiOutlineDocumentText, HiOutlineClock } from 'react-icons/hi2';
import { useState } from 'react';

interface ChatMessageProps {
  message: Message;
  isLatest?: boolean;
}

export default function ChatMessage({ message, isLatest }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [showSources, setShowSources] = useState(false);

  return (
    <div
      className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}
        ${isLatest ? (isUser ? 'animate-slide-in-right' : 'animate-slide-in-left') : ''}`}
    >
      <div className={`max-w-[75%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Avatar + name */}
        <div className={`flex items-center gap-2 mb-1.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {!isUser && (
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#667eea] to-[#764ba2]
                            flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              🤖
            </div>
          )}
          <span className="text-xs text-[var(--text-muted)] font-medium">
            {isUser ? 'Bạn' : 'Chatbot Kinh Tế'}
          </span>
          {isUser && (
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#34d399] to-[#059669]
                            flex items-center justify-center text-xs text-white flex-shrink-0">
              👤
            </div>
          )}
        </div>

        {/* Message bubble */}
        <div
          className={`
            px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words
            ${
              isUser
                ? 'bg-gradient-to-br from-[#667eea]/20 to-[#764ba2]/20 border border-[#667eea]/30 rounded-2xl rounded-br-sm text-[var(--text-primary)]'
                : 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl rounded-bl-sm text-[var(--text-primary)]'
            }
          `}
        >
          {message.content}
        </div>

        {/* Source documents & response time */}
        {!isUser && (message.sources?.length || message.responseTime) && (
          <div className="mt-2 flex items-center gap-3 flex-wrap">
            {message.responseTime !== undefined && (
              <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
                <HiOutlineClock className="w-3 h-3" />
                {message.responseTime}s
              </span>
            )}
            {message.sources && message.sources.length > 0 && (
              <button
                onClick={() => setShowSources(!showSources)}
                className="flex items-center gap-1 text-[10px] text-[var(--accent-primary)]
                           hover:underline cursor-pointer"
              >
                <HiOutlineDocumentText className="w-3 h-3" />
                {showSources ? 'Ẩn' : `Xem ${message.sources.length}`} tài liệu nguồn
              </button>
            )}
          </div>
        )}

        {/* Sources panel */}
        {showSources && message.sources && (
          <div className="mt-2 space-y-2 animate-fade-in">
            {message.sources.map((src, i) => (
              <div
                key={i}
                className="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]
                           text-xs text-[var(--text-secondary)] leading-relaxed"
              >
                <div className="text-[10px] font-semibold text-[var(--accent-primary)] uppercase tracking-wide mb-1">
                  📑 Tài liệu {i + 1} — {src.source?.split('/').pop() || 'Không rõ nguồn'}
                </div>
                <p className="line-clamp-4">{src.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
