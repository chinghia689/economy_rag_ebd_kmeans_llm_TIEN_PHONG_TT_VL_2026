import { Link } from 'react-router-dom';
import {
  HiOutlineArrowRight,
  HiOutlineBanknotes,
  HiOutlineChartBarSquare,
  HiOutlineCheckCircle,
  HiOutlineCircleStack,
  HiOutlineCog6Tooth,
  HiOutlineCpuChip,
  HiOutlineDocumentMagnifyingGlass,
  HiOutlineLockClosed,
  HiOutlineServerStack,
  HiOutlineShieldCheck,
  HiOutlineUsers,
} from 'react-icons/hi2';

const pillars = [
  {
    title: 'Dữ liệu',
    text: 'Vector store được xây từ kho dữ liệu kinh tế Việt Nam, giúp câu trả lời bám theo ngữ cảnh nội bộ thay vì chỉ dựa vào kiến thức nền của model.',
    icon: HiOutlineServerStack,
    tone: 'text-emerald-300',
  },
  {
    title: 'Phương pháp RAG',
    text: 'Pipeline truy xuất tài liệu, chấm lọc ngữ cảnh và sinh câu trả lời từ nguồn đã chọn, phù hợp cho câu hỏi nghiên cứu cần kiểm chứng.',
    icon: HiOutlineDocumentMagnifyingGlass,
    tone: 'text-sky-300',
  },
  {
    title: 'Kiểm soát nguồn',
    text: 'Câu trả lời có danh sách nguồn đi kèm, giúp người dùng đọc lại đoạn dữ liệu liên quan trước khi dùng kết luận.',
    icon: HiOutlineCheckCircle,
    tone: 'text-amber-300',
  },
  {
    title: 'Credit ledger',
    text: 'Mỗi lần nạp, thanh toán và sử dụng chat được ghi thành giao dịch credit theo tài khoản, dễ kiểm tra lại chi phí.',
    icon: HiOutlineCircleStack,
    tone: 'text-rose-300',
  },
  {
    title: 'Bảo mật',
    text: 'JWT, phân quyền admin, secret masking và audit log giúp giảm rủi ro khi vận hành API key, SePay và SQL viewer.',
    icon: HiOutlineLockClosed,
    tone: 'text-violet-300',
  },
  {
    title: 'Vận hành admin',
    text: 'Admin dashboard tập trung tài khoản con, nạp credit, biểu đồ, runtime settings, audit log và SQL viewer read-only.',
    icon: HiOutlineUsers,
    tone: 'text-cyan-300',
  },
];

const pipeline = [
  { title: 'User question', text: 'Người dùng đặt câu hỏi trong hội thoại riêng.', icon: HiOutlineCpuChip },
  { title: 'Retrieval', text: 'Vector store lấy các đoạn dữ liệu kinh tế liên quan.', icon: HiOutlineDocumentMagnifyingGlass },
  { title: 'Grading', text: 'LLM chấm lọc tài liệu để giữ ngữ cảnh hữu ích.', icon: HiOutlineCheckCircle },
  { title: 'Answer', text: 'Sinh câu trả lời dựa trên phần ngữ cảnh đã lọc.', icon: HiOutlineCog6Tooth },
  { title: 'Sources', text: 'Trả về nguồn để người dùng kiểm chứng.', icon: HiOutlineShieldCheck },
  { title: 'Credit log', text: 'Ghi credit sử dụng vào ledger của tài khoản.', icon: HiOutlineCircleStack },
];

const differences = [
  {
    title: 'Không chỉ là một chat box',
    text: 'Sản phẩm có tài khoản, hội thoại, credit balance, payment và admin dashboard để vận hành nhiều người dùng.',
  },
  {
    title: 'Không giấu nguồn sau câu trả lời',
    text: 'Mỗi câu trả lời có nguồn truy xuất, giúp người dùng đọc lại đoạn dữ liệu và giảm rủi ro dùng kết luận thiếu căn cứ.',
  },
  {
    title: 'Không phụ thuộc file cấu hình thủ công',
    text: 'OpenAI, SePay, OAuth, JWT và thông tin ngân hàng được đưa vào SQLite runtime settings, chỉnh được từ admin.',
  },
  {
    title: 'Không bỏ qua vận hành tài chính',
    text: 'Credit ledger và lịch sử giao dịch giúp user lẫn admin kiểm soát chi phí theo từng tài khoản.',
  },
];

const opsMetrics = [
  { label: 'Runtime settings', value: 'SQLite' },
  { label: 'Payment flow', value: 'SePay/VietQR' },
  { label: 'LLM provider', value: 'OpenAI' },
  { label: 'Admin controls', value: 'RBAC + audit' },
];

export default function AboutPage() {
  return (
    <main className="min-h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <section className="relative overflow-hidden border-b border-[var(--border-color)]">
        <img
          src="/economy-ai-hero.png"
          alt="Bối cảnh phân tích kinh tế và trí tuệ nhân tạo"
          className="absolute inset-0 h-full w-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-[rgba(5,8,13,0.8)]" />
        <div className="relative mx-auto grid min-h-[62dvh] w-full max-w-7xl items-end gap-10 px-4 pb-12 pt-28 sm:px-6 lg:grid-cols-[1.08fr_0.92fr] lg:px-8">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-amber-200">Giới thiệu sản phẩm</p>
            <h1 className="mt-5 text-5xl font-semibold leading-[1.04] text-white sm:text-6xl">
              Một hệ thống AI kinh tế được thiết kế để kiểm chứng và vận hành.
            </h1>
          </div>
          <div>
            <p className="text-lg leading-8 text-white/76">
              Trang này mô tả cách sản phẩm xử lý dữ liệu, truy xuất nguồn, ghi credit ledger, bảo vệ cấu hình và hỗ trợ admin vận hành nhiều tài khoản.
            </p>
            <div className="mt-7 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-white/12 bg-white/12">
              {opsMetrics.map((item) => (
                <div key={item.label} className="bg-black/24 px-4 py-3 backdrop-blur-sm">
                  <p className="text-[10px] uppercase tracking-[0.13em] text-white/38">{item.label}</p>
                  <p className="mt-1 text-sm font-semibold text-white">{item.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
        <div className="max-w-3xl">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Product architecture</p>
          <h2 className="mt-4 text-3xl font-semibold leading-tight sm:text-4xl">
            Sáu lớp cốt lõi biến chatbot thành một sản phẩm có thể vận hành.
          </h2>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pillars.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <article key={pillar.title} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
                <Icon className={`h-6 w-6 ${pillar.tone}`} />
                <h3 className="mt-5 text-lg font-semibold">{pillar.title}</h3>
                <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">{pillar.text}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="border-y border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
          <div className="max-w-3xl">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Pipeline</p>
            <h2 className="mt-4 text-3xl font-semibold leading-tight sm:text-4xl">
              User question → Retrieval → Grading → Answer → Sources → Credit log.
            </h2>
          </div>
          <div className="mt-10 grid gap-4 lg:grid-cols-6">
            {pipeline.map((step, index) => {
              const Icon = step.icon;
              return (
                <article key={step.title} className="relative rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <Icon className="h-5 w-5 text-emerald-300" />
                    <span className="text-xs text-[var(--text-muted)]">0{index + 1}</span>
                  </div>
                  <h3 className="mt-5 text-sm font-semibold">{step.title}</h3>
                  <p className="mt-3 text-xs leading-5 text-[var(--text-secondary)]">{step.text}</p>
                </article>
              );
            })}
          </div>
          <div className="mt-6 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4 text-sm leading-6 text-[var(--text-secondary)]">
            Pipeline này tạo dấu vết cho cả phần tri thức và phần chi phí: nguồn nào được dùng, câu trả lời nào được sinh, credit nào bị trừ và giao dịch nào được ghi vào ledger.
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:px-8 lg:py-20">
        <div>
          <p className="flex items-center gap-2 text-sm font-medium text-sky-300"><HiOutlineChartBarSquare className="h-4 w-4" /> What makes this different</p>
          <h2 className="mt-4 text-3xl font-semibold leading-tight sm:text-4xl">Khác biệt nằm ở lớp vận hành, không chỉ ở câu trả lời AI.</h2>
          <p className="mt-4 text-base leading-7 text-[var(--text-secondary)]">
            Một demo chatbot thường dừng ở input và output. Sản phẩm này thêm nguồn, ledger, payment, runtime settings và audit log để dùng được trong môi trường nhiều tài khoản.
          </p>
        </div>
        <div className="space-y-4">
          {differences.map((item) => (
            <article key={item.title} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-t border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_1fr] lg:px-8 lg:py-20">
          <div>
            <p className="flex items-center gap-2 text-sm font-medium text-emerald-300"><HiOutlineShieldCheck className="h-4 w-4" /> Bảo mật và kiểm soát</p>
            <h2 className="mt-4 text-3xl font-semibold leading-tight sm:text-4xl">Admin có quyền chỉnh hệ thống, nhưng mọi thao tác quan trọng đều có dấu vết.</h2>
          </div>
          <div>
            <p className="text-base leading-7 text-[var(--text-secondary)]">
              Secret được mask trong giao diện, SQL viewer chỉ cho read-only query, quyền admin được kiểm tra bằng RBAC và các thao tác như nạp credit, đổi setting, cấp quyền admin hoặc chạy SQL viewer được ghi audit log.
            </p>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                <HiOutlineBanknotes className="h-5 w-5 text-amber-300" />
                <p className="mt-3 text-sm font-semibold">Credit ledger</p>
                <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">Nạp tiền, nạp thủ công và sử dụng chat đều có transaction riêng.</p>
              </div>
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                <HiOutlineShieldCheck className="h-5 w-5 text-emerald-300" />
                <p className="mt-3 text-sm font-semibold">Audit log</p>
                <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">Theo dõi ai đã thay đổi cấu hình, quyền hoặc dữ liệu vận hành.</p>
              </div>
            </div>
            <Link
              to="/chat"
              className="mt-7 inline-flex h-11 w-fit items-center justify-center gap-2 rounded-lg bg-[var(--text-primary)] px-5 text-sm font-semibold text-[var(--bg-primary)] transition-opacity hover:opacity-90"
            >
              Mở chatbot
              <HiOutlineArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
