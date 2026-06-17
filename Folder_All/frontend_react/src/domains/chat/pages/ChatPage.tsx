import { useRef, useEffect, useCallback } from 'react';
import { useChatStore } from '../chatStore';
import { sendConversationMessage, getErrorMessage } from '../../../services/api';
import { useAuthStore } from '../../auth/authStore';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import TypingIndicator from '../components/TypingIndicator';
import EmptyState from '../components/EmptyState';
import { HiOutlineCircleStack, HiOutlineLockClosed, HiOutlineSparkles } from 'react-icons/hi2';
import type { Message } from '../../../types';

const MAX_QUESTION_CHARS = 4000;
function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function streamText(
  text: string,
  update: (content: string) => void,
  chunkSize = 22,
) {
  let current = '';
  for (let index = 0; index < text.length; index += chunkSize) {
    current += text.slice(index, index + chunkSize);
    update(current);
    await wait(18);
  }
}

interface ChatPageProps {
  onOpenLogin: () => void;
}

export default function ChatPage({ onOpenLogin }: ChatPageProps) {
  const {
    activeConversationId,
    isSending,
    createConversation,
    addMessage,
    updateLastBotMessage,
    setIsSending,
    setError,
    getActiveMessages,
  } = useChatStore();
  const { isAuthenticated, isLoading, tokenBalance, refreshBalance } = useAuthStore();

  const messages = getActiveMessages();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const loginRequired = !isLoading && !isAuthenticated;
  const inputBlocked = loginRequired || (isAuthenticated && tokenBalance !== null && tokenBalance <= 0);
  const helperText = loginRequired
    ? 'Vui lòng đăng nhập để bắt đầu chat.'
    : inputBlocked
      ? 'Bạn đã hết credit. Vui lòng nạp thêm credit để tiếp tục.'
      : `Credit còn lại: ${tokenBalance ?? '...'}`;

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  useEffect(() => {
    if (loginRequired) {
      onOpenLogin();
    }
  }, [loginRequired, onOpenLogin]);

  const handleSend = useCallback(
    async (text: string) => {
      if (text.length > MAX_QUESTION_CHARS) {
        setError(`Câu hỏi quá dài. Tối đa ${MAX_QUESTION_CHARS} ký tự.`);
        return;
      }

      if (!isAuthenticated) {
        setError('Vui lòng đăng nhập để hỏi và lưu lịch sử hội thoại.');
        onOpenLogin();
        return;
      }

      if (tokenBalance !== null && tokenBalance <= 0) {
        setError('Bạn đã hết credit. Vui lòng nạp thêm credit để tiếp tục.');
        return;
      }

      let convId = activeConversationId;
      if (!convId) {
        convId = await createConversation();
      }

      // Add user message
      const userMsg: Message = {
        id: Date.now().toString(36) + '_u',
        role: 'user',
        content: text,
        timestamp: Date.now(),
      };
      addMessage(userMsg);

      // Add placeholder bot message
      const botMsg: Message = {
        id: Date.now().toString(36) + '_b',
        role: 'bot',
        content: '',
        timestamp: Date.now(),
      };
      addMessage(botMsg);

      setIsSending(true);
      setError(null);

      try {
        const res = await sendConversationMessage(convId, text);

        if (res.success && res.data) {
          updateLastBotMessage('', res.data.sources, res.data.response_time, res.data.token_used);
          await streamText(res.data.answer, (content) => {
            updateLastBotMessage(content, res.data?.sources, res.data?.response_time, res.data?.token_used);
          });
          void refreshBalance();
        } else {
          const fallbackAnswer = res.message || 'Không thể tạo câu trả lời.';
          await streamText(fallbackAnswer, (content) => updateLastBotMessage(content));
        }
      } catch (err: unknown) {
        const message = getErrorMessage(err, 'Không thể kết nối đến server.');
        await streamText(`Lỗi: ${message}`, (content) => updateLastBotMessage(content));
        setError(message);
      } finally {
        setIsSending(false);
      }
    },
    [
      activeConversationId,
      createConversation,
      addMessage,
      updateLastBotMessage,
      setIsSending,
      setError,
      isAuthenticated,
      tokenBalance,
      refreshBalance,
      onOpenLogin,
    ]
  );

  const handleRegenerate = useCallback(() => {
    const lastUserMessage = [...messages].reverse().find((message) => message.role === 'user');
    if (lastUserMessage && !isSending) {
      void handleSend(lastUserMessage.content);
    }
  }, [handleSend, isSending, messages]);

  // Filter out the empty placeholder when sending
  const visibleMessages = messages.filter(
    (m, i) => !(m.role === 'bot' && m.content === '' && i === messages.length - 1 && isSending)
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-[var(--bg-primary)]">
      {visibleMessages.length > 0 && (
        <div className="flex flex-none items-center justify-between gap-4 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]/80 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-500/25 bg-emerald-500/12 text-emerald-200">
              <HiOutlineSparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[var(--text-primary)]">Economic research session</p>
              <p className="truncate text-xs text-[var(--text-muted)]">Nguồn RAG, credit ledger và lịch sử hội thoại theo tài khoản</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 py-2 text-xs text-[var(--text-secondary)] sm:flex">
            <HiOutlineCircleStack className="h-4 w-4 text-amber-300" />
            {isAuthenticated ? `${tokenBalance ?? '...'} credit` : 'Cần đăng nhập'}
          </div>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain">
        {visibleMessages.length === 0 && !isSending ? (
          <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center px-4">
            {loginRequired && (
              <div className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-3">
                    <HiOutlineLockClosed className="mt-0.5 h-5 w-5 shrink-0" />
                    <div>
                      <p className="font-semibold">Cần đăng nhập để sử dụng Chat</p>
                      <p className="mt-1 text-xs leading-5 text-amber-100/80">Hệ thống chỉ cho phép tài khoản đã đăng nhập gửi câu hỏi, lưu hội thoại và trừ credit.</p>
                    </div>
                  </div>
                  <button
                    onClick={onOpenLogin}
                    className="h-10 rounded-lg bg-amber-200 px-4 text-sm font-semibold text-slate-950 transition-opacity hover:opacity-90"
                  >
                    Đăng nhập
                  </button>
                </div>
              </div>
            )}
            <EmptyState onSuggest={handleSend} />
          </div>
        ) : (
          <div className="mx-auto w-full max-w-4xl space-y-4 px-4 py-6">
            {visibleMessages.map((msg, i) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isLatest={i === visibleMessages.length - 1}
                onRegenerate={msg.role === 'bot' && i === visibleMessages.length - 1 ? handleRegenerate : undefined}
              />
            ))}
            {isSending && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <ChatInput
        onSend={handleSend}
        disabled={isSending || inputBlocked}
        helperText={helperText}
        placeholder={loginRequired ? 'Đăng nhập để bắt đầu chat' : inputBlocked ? 'Hết credit' : undefined}
      />
    </div>
  );
}
