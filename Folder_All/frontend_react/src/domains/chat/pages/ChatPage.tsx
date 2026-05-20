import { useRef, useEffect, useCallback } from 'react';
import { useChatStore } from '../chatStore';
import { sendChatMessage, sendConversationMessage, getErrorMessage } from '../../../services/api';
import { useAuthStore } from '../../auth/authStore';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import TypingIndicator from '../components/TypingIndicator';
import EmptyState from '../components/EmptyState';
import type { Message } from '../../../types';

const MAX_QUESTION_CHARS = 4000;
const GUEST_DAILY_QUESTION_LIMIT = 5;

function getGuestUsageKey(): string {
  return `guest_chat_count_${new Date().toISOString().slice(0, 10)}`;
}

function getGuestQuestionCount(): number {
  return Number(localStorage.getItem(getGuestUsageKey()) || '0');
}

function incrementGuestQuestionCount() {
  localStorage.setItem(getGuestUsageKey(), String(getGuestQuestionCount() + 1));
}

export default function ChatPage() {
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
  const { isAuthenticated, tokenBalance, refreshBalance } = useAuthStore();

  const messages = getActiveMessages();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputBlocked = isAuthenticated && tokenBalance !== null && tokenBalance <= 0;
  const helperText = inputBlocked
    ? 'Bạn đã hết token. Vui lòng nạp thêm token để tiếp tục.'
    : isAuthenticated
      ? `Token còn lại: ${tokenBalance ?? '...'}`
      : `Guest mode: còn ${Math.max(0, GUEST_DAILY_QUESTION_LIMIT - getGuestQuestionCount())} lượt hỏi hôm nay.`;

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleSend = useCallback(
    async (text: string) => {
      if (text.length > MAX_QUESTION_CHARS) {
        setError(`Câu hỏi quá dài. Tối đa ${MAX_QUESTION_CHARS} ký tự.`);
        return;
      }

      if (!isAuthenticated && getGuestQuestionCount() >= GUEST_DAILY_QUESTION_LIMIT) {
        setError('Guest đã hết lượt hỏi hôm nay. Vui lòng đăng nhập để tiếp tục.');
        return;
      }

      if (isAuthenticated && tokenBalance !== null && tokenBalance <= 0) {
        setError('Bạn đã hết token. Vui lòng nạp thêm token để tiếp tục.');
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
        const res = isAuthenticated
          ? await sendConversationMessage(convId, text)
          : await sendChatMessage(text);

        if (res.success && res.data) {
          updateLastBotMessage(
            res.data.answer,
            res.data.sources,
            res.data.response_time,
            res.data.token_used
          );
          if (isAuthenticated) {
            void refreshBalance();
          } else {
            incrementGuestQuestionCount();
          }
        } else {
          updateLastBotMessage(
            res.message || 'Không thể tạo câu trả lời.',
          );
        }
      } catch (err: unknown) {
        const message = getErrorMessage(err, 'Không thể kết nối đến server.');
        updateLastBotMessage(
          `❌ Lỗi: ${message}`,
        );
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
    ]
  );

  // Filter out the empty placeholder when sending
  const visibleMessages = messages.filter(
    (m, i) => !(m.role === 'bot' && m.content === '' && i === messages.length - 1 && isSending)
  );

  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg-primary)]">
      {/* ── Messages Area ── */}
      <div className="flex-1 overflow-y-auto">
        {visibleMessages.length === 0 && !isSending ? (
          <EmptyState onSuggest={handleSend} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-2">
            {visibleMessages.map((msg, i) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isLatest={i === visibleMessages.length - 1}
              />
            ))}
            {isSending && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* ── Input ── */}
      <ChatInput
        onSend={handleSend}
        disabled={isSending || inputBlocked}
        helperText={helperText}
        placeholder={inputBlocked ? 'Hết token' : undefined}
      />
    </div>
  );
}
