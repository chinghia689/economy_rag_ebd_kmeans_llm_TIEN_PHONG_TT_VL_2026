import {
  HiOutlineBanknotes,
  HiOutlineBookOpen,
  HiOutlineBuildingOffice2,
  HiOutlineChartBarSquare,
  HiOutlineChatBubbleLeftRight,
  HiOutlineDocumentMagnifyingGlass,
  HiOutlineScale,
  HiOutlineSparkles,
} from 'react-icons/hi2';

interface EmptyStateProps {
  onSuggest: (question: string) => void;
}

const topicGroups = [
  {
    title: 'Vĩ mô',
    icon: HiOutlineChartBarSquare,
    questions: ['GDP Việt Nam năm 2024 đạt bao nhiêu?', 'Lạm phát ảnh hưởng thế nào đến tiêu dùng?'],
  },
  {
    title: 'Doanh nghiệp',
    icon: HiOutlineBuildingOffice2,
    questions: ['Doanh nghiệp xuất khẩu chịu tác động gì khi tỷ giá biến động?', 'Chi phí vốn ảnh hưởng ra sao tới lợi nhuận doanh nghiệp?'],
  },
  {
    title: 'Thị trường',
    icon: HiOutlineBanknotes,
    questions: ['Tình hình xuất nhập khẩu Việt Nam hiện nay?', 'Yếu tố nào ảnh hưởng đến cầu tiêu dùng nội địa?'],
  },
  {
    title: 'Chính sách',
    icon: HiOutlineScale,
    questions: ['Chính sách tiền tệ gần đây có điểm gì nổi bật?', 'Đầu tư công tác động thế nào tới tăng trưởng?'],
  },
];

export default function EmptyState({ onSuggest }: EmptyStateProps) {
  return (
    <div className="flex min-h-full w-full flex-none items-center justify-center px-4 py-10 animate-fade-in sm:px-8">
      <div className="w-full max-w-5xl">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-lg border border-emerald-500/25 bg-emerald-500/12 text-emerald-200 shadow-lg">
          <HiOutlineChatBubbleLeftRight className="h-8 w-8" />
        </div>

        <div className="mx-auto mt-6 max-w-2xl text-center">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Research workspace</p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight text-[var(--text-primary)]">
            Chọn một chủ đề hoặc đặt câu hỏi kinh tế của bạn.
          </h2>
          <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
            Câu trả lời có nguồn RAG, credit ledger và lịch sử hội thoại theo tài khoản.
          </p>
        </div>

        <div className="mt-8 flex items-center justify-center gap-3 text-xs text-[var(--text-muted)]">
          <span className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border-color)] px-3">
            <HiOutlineSparkles className="h-4 w-4 text-emerald-300" /> GT1 ERC
          </span>
          <span className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border-color)] px-3">
            <HiOutlineBookOpen className="h-4 w-4 text-sky-300" /> Có nguồn
          </span>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-4">
          {topicGroups.map((group) => {
            const Icon = group.icon;
            return (
              <section key={group.title} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] p-4">
                <div className="flex items-center gap-2 border-b border-[var(--border-color)] pb-3">
                  <Icon className="h-5 w-5 text-emerald-300" />
                  <h3 className="text-sm font-semibold">{group.title}</h3>
                </div>
                <div className="mt-3 space-y-2">
                  {group.questions.map((question) => (
                    <button
                      key={question}
                      onClick={() => onSuggest(question)}
                      className="flex min-h-16 w-full items-start gap-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-3 text-left text-xs leading-5 text-[var(--text-secondary)] transition-colors hover:border-emerald-500/35 hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                    >
                      <HiOutlineDocumentMagnifyingGlass className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                      <span>{question}</span>
                    </button>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}
