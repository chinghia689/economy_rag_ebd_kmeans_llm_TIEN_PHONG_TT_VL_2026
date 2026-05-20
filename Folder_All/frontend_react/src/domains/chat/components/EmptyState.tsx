import { HiOutlineChatBubbleLeftRight, HiOutlineSparkles, HiOutlineBookOpen } from 'react-icons/hi2';

interface EmptyStateProps {
  onSuggest: (question: string) => void;
}

const suggestions = [
  { icon: '📊', text: 'GDP Việt Nam năm 2024 đạt bao nhiêu?' },
  { icon: '💹', text: 'Lạm phát ảnh hưởng thế nào đến kinh tế?' },
  { icon: '🏦', text: 'Chính sách tiền tệ của Ngân hàng Nhà nước?' },
  { icon: '📈', text: 'Tình hình xuất nhập khẩu Việt Nam?' },
];

export default function EmptyState({ onSuggest }: EmptyStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8 animate-fade-in">
      <div className="text-center max-w-lg">
        {/* Logo */}
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[#667eea] to-[#764ba2]
                        flex items-center justify-center shadow-lg"
             style={{ animation: 'glow 3s ease-in-out infinite' }}>
          <HiOutlineChatBubbleLeftRight className="w-10 h-10 text-white" />
        </div>

        <h2 className="text-2xl font-bold bg-gradient-to-r from-[#667eea] to-[#764ba2]
                        bg-clip-text text-transparent mb-2">
          Chatbot Kinh Tế Việt Nam
        </h2>
        <p className="text-sm text-[var(--text-secondary)] mb-8 leading-relaxed">
          Hỏi đáp thông minh về kinh tế sử dụng<br />
          <span className="text-[var(--accent-primary)] font-medium">RAG + Energy-Based Distance Retriever</span>
        </p>

        {/* Feature badges */}
        <div className="flex items-center justify-center gap-3 mb-8 flex-wrap">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs
                           bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border border-[var(--accent-primary)]/20">
            <HiOutlineSparkles className="w-3.5 h-3.5" /> AI Powered
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs
                           bg-[var(--success)]/10 text-[var(--success)] border border-[var(--success)]/20">
            <HiOutlineBookOpen className="w-3.5 h-3.5" /> Dữ liệu kinh tế VN
          </span>
        </div>

        {/* Suggestion cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggest(s.text)}
              className="flex items-start gap-3 p-3.5 rounded-xl border border-[var(--border-color)]
                         bg-[var(--bg-card)] hover:border-[var(--accent-primary)]/50 hover:bg-[var(--bg-hover)]
                         transition-all duration-200 text-left cursor-pointer group"
            >
              <span className="text-lg mt-0.5">{s.icon}</span>
              <span className="text-xs text-[var(--text-secondary)] leading-relaxed
                               group-hover:text-[var(--text-primary)] transition-colors">
                {s.text}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
