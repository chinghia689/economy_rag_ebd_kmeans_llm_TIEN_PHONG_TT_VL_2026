import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  HiOutlineArrowPath,
  HiOutlineArrowRight,
  HiOutlineBanknotes,
  HiOutlineCheckCircle,
  HiOutlineCircleStack,
  HiOutlineClock,
  HiOutlineCog6Tooth,
  HiOutlineDocumentMagnifyingGlass,
  HiOutlineServerStack,
  HiOutlineShieldCheck,
  HiOutlineSparkles,
} from 'react-icons/hi2';

interface HomePageProps {
  onOpenPayment: () => void;
}

const demoQuestions = [
  'Tác động của lạm phát tới tiêu dùng Việt Nam?',
  'Xuất nhập khẩu ảnh hưởng thế nào tới tăng trưởng GDP?',
];

const demoAnswers: Record<string, { answer: string; sources: string[]; credits: number; time: string }> = {
  'Tác động của lạm phát tới tiêu dùng Việt Nam?': {
    answer: 'Lạm phát làm giảm sức mua thực tế, khiến hộ gia đình ưu tiên hàng thiết yếu và trì hoãn các khoản chi không cấp bách. Với doanh nghiệp, chi phí đầu vào tăng có thể thu hẹp biên lợi nhuận nếu không chuyển được vào giá bán.',
    sources: ['Báo cáo CPI và sức mua hộ gia đình', 'Tổng quan thị trường bán lẻ Việt Nam'],
    credits: 1,
    time: '1.8s',
  },
  'Xuất nhập khẩu ảnh hưởng thế nào tới tăng trưởng GDP?': {
    answer: 'Xuất khẩu tạo đóng góp trực tiếp vào tổng cầu, trong khi nhập khẩu phản ánh nhu cầu nguyên liệu và máy móc cho sản xuất. Khi đơn hàng xuất khẩu phục hồi, tác động lan toả thường xuất hiện ở sản xuất công nghiệp, logistics và việc làm.',
    sources: ['Dữ liệu thương mại hàng hoá Việt Nam', 'Báo cáo sản xuất công nghiệp và logistics'],
    credits: 1,
    time: '2.1s',
  },
};

const trustSignals = [
  {
    icon: HiOutlineDocumentMagnifyingGlass,
    title: 'Dữ liệu nội bộ',
    text: 'Vector store từ kho dữ liệu kinh tế Việt Nam, phục vụ truy xuất theo ngữ cảnh.',
    tone: 'text-emerald-300',
  },
  {
    icon: HiOutlineSparkles,
    title: 'RAG có nguồn',
    text: 'Câu trả lời đi kèm đoạn nguồn để người dùng kiểm chứng thay vì chỉ đọc kết luận.',
    tone: 'text-sky-300',
  },
  {
    icon: HiOutlineBanknotes,
    title: 'Thanh toán SePay',
    text: 'Nạp credit bằng VietQR/SePay và tự cộng credit khi giao dịch được khớp.',
    tone: 'text-amber-300',
  },
  {
    icon: HiOutlineCog6Tooth,
    title: 'Quản trị credit',
    text: 'Admin xem tài khoản con, nạp credit thủ công và kiểm tra audit log.',
    tone: 'text-rose-300',
  },
];

const heroStats = [
  { label: 'Model', value: 'gpt-5-mini' },
  { label: 'Pipeline', value: 'Gt2_mutiquery ERC' },
  { label: 'Balance', value: '128 credit' },
  { label: 'Status', value: 'Online' },
];

function ProductChatScreen({ question }: { question: string }) {
  const demo = demoAnswers[question];

  return (
    <div className="rounded-lg border border-white/12 bg-[#0b1017]/88 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between gap-4 border-b border-white/10 px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-400/25 bg-emerald-400/10 text-emerald-200">
            <HiOutlineSparkles className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">Economic AI session</p>
            <p className="truncate text-xs text-white/45">Nguồn RAG · credit ledger · lịch sử hội thoại</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs text-emerald-200">
          <span className="h-2 w-2 rounded-full bg-emerald-300" />
          Model ready
        </div>
      </div>

      <div className="grid gap-px border-b border-white/10 bg-white/10 sm:grid-cols-4">
        {heroStats.map((item) => (
          <div key={item.label} className="bg-black/22 px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.13em] text-white/38">{item.label}</p>
            <p className="mt-1 text-sm font-semibold text-white">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="space-y-4 p-4">
        <div className="ml-auto max-w-[88%] rounded-lg rounded-tr-sm border border-sky-400/25 bg-sky-400/10 px-4 py-3 text-sm leading-6 text-white">
          {question}
        </div>
        <div className="max-w-[92%] rounded-lg rounded-tl-sm border border-white/10 bg-white/[0.06] px-4 py-3 text-sm leading-6 text-white/86">
          {demo.answer}
        </div>

        <div className="grid gap-3 sm:grid-cols-[1fr_0.72fr]">
          <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-3">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-emerald-200">
              <HiOutlineDocumentMagnifyingGlass className="h-4 w-4" />
              Nguồn trích dẫn
            </div>
            <div className="space-y-2">
              {demo.sources.map((source, index) => (
                <div key={source} className="rounded-md bg-black/20 px-3 py-2 text-xs leading-5 text-white/70">
                  {index + 1}. {source}
                </div>
              ))}
            </div>
          </div>
          <div className="grid gap-3">
            <div className="rounded-lg border border-amber-400/20 bg-amber-400/10 p-3">
              <p className="text-[11px] uppercase tracking-[0.13em] text-amber-200/70">Credit used</p>
              <p className="mt-1 text-2xl font-semibold text-amber-100">-{demo.credits.toLocaleString('vi-VN')}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
              <p className="flex items-center gap-1 text-[11px] uppercase tracking-[0.13em] text-white/45"><HiOutlineClock className="h-3.5 w-3.5" /> Response</p>
              <p className="mt-1 text-2xl font-semibold text-white">{demo.time}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LiveProductPreview() {
  const [selectedQuestion, setSelectedQuestion] = useState(demoQuestions[0]);
  const demo = demoAnswers[selectedQuestion];
  const remaining = useMemo(() => 2 - demoQuestions.indexOf(selectedQuestion), [selectedQuestion]);

  return (
    <section className="mx-auto grid w-full max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[0.82fr_1.18fr] lg:px-8 lg:py-20">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Live product preview</p>
        <h2 className="mt-4 text-3xl font-semibold leading-tight sm:text-4xl">
          Thử nhanh trải nghiệm chat, nguồn và ledger trước khi đăng nhập.
        </h2>
        <p className="mt-5 text-base leading-7 text-[var(--text-secondary)]">
          Preview này mô phỏng luồng sản phẩm thật: câu hỏi, câu trả lời, nguồn trích dẫn, credit sử dụng và trạng thái model trong cùng một màn hình.
        </p>
        <div className="mt-7 space-y-3">
          {demoQuestions.map((question) => (
            <button
              key={question}
              onClick={() => setSelectedQuestion(question)}
              className={`flex w-full items-start gap-3 rounded-lg border p-4 text-left transition-colors ${
                selectedQuestion === question
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-[var(--text-primary)]'
                  : 'border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
              }`}
            >
              <HiOutlineSparkles className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300" />
              <span className="text-sm leading-6">{question}</span>
            </button>
          ))}
        </div>
        <p className="mt-4 text-xs text-[var(--text-muted)]">Preview còn {Math.max(1, remaining)} câu mẫu. Dùng thật ở trang Chat để lưu lịch sử và tính credit theo tài khoản.</p>
      </div>

      <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
        <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-4">
          <div className="flex items-center gap-2">
            <HiOutlineServerStack className="h-5 w-5 text-emerald-300" />
            <span className="text-sm font-semibold">Demo response</span>
          </div>
          <span className="rounded-lg bg-emerald-500/12 px-2 py-1 text-xs text-emerald-300">gpt-5-mini</span>
        </div>
        <div className="mt-5 space-y-4">
          <div className="rounded-lg border border-sky-500/25 bg-sky-500/10 p-4 text-sm leading-6">
            {selectedQuestion}
          </div>
          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4 text-sm leading-7 text-[var(--text-secondary)]">
            {demo.answer}
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-3">
              <HiOutlineDocumentMagnifyingGlass className="h-5 w-5 text-emerald-300" />
              <p className="mt-3 text-xs text-[var(--text-muted)]">Nguồn</p>
              <p className="mt-1 text-xl font-semibold">{demo.sources.length}</p>
            </div>
            <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-3">
              <HiOutlineCircleStack className="h-5 w-5 text-amber-300" />
              <p className="mt-3 text-xs text-[var(--text-muted)]">Credit</p>
              <p className="mt-1 text-xl font-semibold">{demo.credits.toLocaleString('vi-VN')}</p>
            </div>
            <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-3">
              <HiOutlineClock className="h-5 w-5 text-sky-300" />
              <p className="mt-3 text-xs text-[var(--text-muted)]">Thời gian</p>
              <p className="mt-1 text-xl font-semibold">{demo.time}</p>
            </div>
          </div>
          <Link
            to="/chat"
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-[var(--text-primary)] px-4 text-sm font-semibold text-[var(--bg-primary)] transition-opacity hover:opacity-90"
          >
            Mở chat thật
            <HiOutlineArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function HomePage({ onOpenPayment }: HomePageProps) {
  const [heroQuestion, setHeroQuestion] = useState(demoQuestions[0]);

  return (
    <main className="min-h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <section className="relative overflow-hidden border-b border-[var(--border-color)]">
        <img
          src="/economy-ai-hero.png"
          alt="Không gian phân tích dữ liệu kinh tế bằng AI"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(5,8,13,0.92)_0%,rgba(5,8,13,0.74)_48%,rgba(5,8,13,0.45)_100%)]" />
        <div className="relative mx-auto grid min-h-[86dvh] w-full max-w-7xl items-end gap-10 px-4 pb-10 pt-28 sm:px-6 lg:grid-cols-[0.92fr_1.08fr] lg:px-8">
          <div className="pb-2">
            <p className="mb-5 text-sm font-medium uppercase tracking-[0.2em] text-emerald-300">
              AI cho dữ liệu kinh tế Việt Nam
            </p>
            <h1 className="text-5xl font-semibold leading-[1.02] text-white sm:text-6xl lg:text-7xl">
              Trợ lý nghiên cứu kinh tế Việt Nam
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-white/78 sm:text-xl">
              Có nguồn, có lịch sử, có kiểm soát chi phí.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/chat"
                className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-slate-950 transition-opacity hover:opacity-90"
              >
                Bắt đầu chat
                <HiOutlineArrowRight className="h-4 w-4" />
              </Link>
              <button
                onClick={onOpenPayment}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-white/35 px-5 text-sm font-semibold text-white transition-colors hover:bg-white/10"
              >
                <HiOutlineBanknotes className="h-4 w-4" />
                Nạp credit
              </button>
            </div>
            <div className="mt-8 flex flex-wrap gap-2 text-xs text-white/60">
              <button onClick={() => setHeroQuestion(demoQuestions[0])} className="rounded-lg border border-white/15 px-3 py-2 transition-colors hover:bg-white/10">Demo CPI</button>
              <button onClick={() => setHeroQuestion(demoQuestions[1])} className="rounded-lg border border-white/15 px-3 py-2 transition-colors hover:bg-white/10">Demo xuất nhập khẩu</button>
              <span className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-emerald-200">Model ready</span>
            </div>
          </div>

          <div className="w-full pb-2">
            <ProductChatScreen question={heroQuestion} />
          </div>
        </div>
      </section>

      <LiveProductPreview />

      <section className="border-y border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Trust signals</p>
              <h2 className="mt-4 text-3xl font-semibold leading-tight sm:text-4xl">Đủ lớp để dùng như một sản phẩm thật.</h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-[var(--text-secondary)]">
              Không chỉ là chatbot demo: hệ thống có dữ liệu, nguồn, thanh toán, credit ledger, admin dashboard và lịch sử giao dịch.
            </p>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {trustSignals.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-5">
                  <Icon className={`h-6 w-6 ${item.tone}`} />
                  <h3 className="mt-5 text-base font-semibold">{item.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">{item.text}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_1fr] lg:px-8 lg:py-20">
        <div>
          <p className="flex items-center gap-2 text-sm font-medium text-emerald-300"><HiOutlineShieldCheck className="h-4 w-4" /> Runtime và vận hành</p>
          <h2 className="mt-4 text-3xl font-semibold leading-tight sm:text-4xl">API key, SePay, model và quyền admin nằm trong dashboard.</h2>
        </div>
        <div>
          <p className="text-base leading-7 text-[var(--text-secondary)]">
            Admin có thể đổi OpenAI key, model, SePay key, ngân hàng, nạp credit cho tài khoản con và xem audit log. Người dùng có thể xem lịch sử giao dịch credit của chính mình.
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
              <HiOutlineCheckCircle className="h-5 w-5 text-emerald-300" />
              <p className="mt-3 text-sm font-semibold">Lịch sử giao dịch</p>
              <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">Credit nạp, credit dùng và payment được lưu trong ledger.</p>
            </div>
            <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
              <HiOutlineArrowPath className="h-5 w-5 text-sky-300" />
              <p className="mt-3 text-sm font-semibold">Cấu hình realtime</p>
              <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">Đổi key/model trong DB, không cần sửa file cấu hình.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
