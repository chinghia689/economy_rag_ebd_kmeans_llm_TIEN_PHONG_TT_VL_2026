import { useState, useRef, useEffect } from 'react';
import { HiOutlinePaperAirplane } from 'react-icons/hi2';

interface ChatInputProps {
  onSend: (msg: string) => void;
  disabled: boolean;
  helperText?: string;
  placeholder?: string;
}

export default function ChatInput({ onSend, disabled, helperText, placeholder }: ChatInputProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 150) + 'px';
    }
  }, [text]);

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-4 border-t border-[var(--border-color)] bg-[var(--bg-secondary)]/80 backdrop-blur-lg">
      <div className="max-w-3xl mx-auto">
        <div
          className={`
            flex items-end gap-2 rounded-2xl border bg-[var(--bg-card)] px-4 py-2.5
            transition-all duration-200
            ${disabled
              ? 'border-[var(--border-color)] opacity-60'
              : 'border-[var(--border-color)] focus-within:border-[var(--accent-primary)] focus-within:shadow-[var(--shadow-glow)]'
            }
          `}
        >
          <textarea
            ref={textareaRef}
            id="chat-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder || (disabled ? 'Không thể gửi lúc này' : 'Nhập câu hỏi về kinh tế Việt Nam...')}
            rows={1}
            className="flex-1 bg-transparent text-sm text-[var(--text-primary)]
                       placeholder:text-[var(--text-muted)] resize-none outline-none
                       leading-relaxed py-1 max-h-[150px]"
          />
          <button
            id="btn-send"
            onClick={handleSubmit}
            disabled={disabled || !text.trim()}
            className={`
              flex-shrink-0 p-2 rounded-xl transition-all duration-200 cursor-pointer
              ${
                disabled || !text.trim()
                  ? 'text-[var(--text-muted)] cursor-not-allowed'
                  : 'text-white bg-gradient-to-r from-[#667eea] to-[#764ba2] hover:opacity-90 shadow-lg'
              }
            `}
          >
            <HiOutlinePaperAirplane className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-[10px] text-[var(--text-muted)] mt-2">
          {helperText || 'Nhấn Enter để gửi, Shift+Enter để xuống dòng'}
        </p>
      </div>
    </div>
  );
}
