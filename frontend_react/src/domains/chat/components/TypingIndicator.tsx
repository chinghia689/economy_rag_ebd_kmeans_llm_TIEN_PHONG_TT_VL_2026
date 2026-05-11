export default function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4 animate-fade-in">
      <div className="max-w-[75%]">
        {/* Avatar + name */}
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#667eea] to-[#764ba2]
                          flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
            🤖
          </div>
          <span className="text-xs text-[var(--text-muted)] font-medium">Chatbot Kinh Tế</span>
        </div>

        {/* Typing bubble */}
        <div className="px-5 py-3.5 bg-[var(--bg-card)] border border-[var(--border-color)]
                        rounded-2xl rounded-bl-sm inline-flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)]"
                style={{ animation: 'pulse-dot 1.4s infinite ease-in-out', animationDelay: '0s' }} />
          <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)]"
                style={{ animation: 'pulse-dot 1.4s infinite ease-in-out', animationDelay: '0.2s' }} />
          <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)]"
                style={{ animation: 'pulse-dot 1.4s infinite ease-in-out', animationDelay: '0.4s' }} />
        </div>

        <p className="text-[10px] text-[var(--text-muted)] mt-1.5 ml-1">
          Đang truy xuất và phân tích tài liệu...
        </p>
      </div>
    </div>
  );
}
