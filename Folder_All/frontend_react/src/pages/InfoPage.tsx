import { Link } from 'react-router-dom';
import { HiOutlineArrowRight, HiOutlineShieldCheck } from 'react-icons/hi2';

const content: Record<string, { title: string; lead: string; items: string[] }> = {
  docs: {
    title: 'Tài liệu sử dụng',
    lead: 'Các luồng chính của sản phẩm: chat có nguồn, nạp credit, xem lịch sử giao dịch và quản trị admin.',
    items: ['Đăng nhập để lưu hội thoại và credit balance.', 'Dùng trang Chat để đặt câu hỏi kinh tế.', 'Mở Lịch sử để kiểm tra credit đã nạp và đã dùng.'],
  },
  security: {
    title: 'Bảo mật',
    lead: 'Hệ thống dùng JWT, RBAC cho admin, secret masking và audit log cho thao tác nhạy cảm.',
    items: ['SQL viewer chỉ cho SELECT hoặc PRAGMA.', 'Secret API key không hiển thị raw trong admin.', 'Cấp/gỡ admin, nạp credit, đổi setting đều có audit log.'],
  },
  terms: {
    title: 'Điều khoản',
    lead: 'Dịch vụ phục vụ tra cứu và nghiên cứu thông tin kinh tế, không thay thế tư vấn tài chính hoặc pháp lý chuyên nghiệp.',
    items: ['Người dùng chịu trách nhiệm kiểm chứng nguồn trước khi ra quyết định.', 'Credit đã sử dụng không được hoàn lại.', 'Không dùng hệ thống cho hành vi vi phạm pháp luật.'],
  },
  privacy: {
    title: 'Quyền riêng tư',
    lead: 'Hệ thống lưu email đăng nhập, hội thoại, credit ledger và payment record để vận hành tài khoản.',
    items: ['Không công khai hội thoại giữa các tài khoản.', 'Admin có thể xem dữ liệu vận hành cần thiết.', 'Secret và API key được mask trong giao diện.'],
  },
};

export default function InfoPage({ type }: { type: keyof typeof content }) {
  const page = content[type];
  return (
    <main className="min-h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <section className="mx-auto w-full max-w-4xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Public information</p>
        <h1 className="mt-4 text-5xl font-semibold leading-tight">{page.title}</h1>
        <p className="mt-5 text-base leading-7 text-[var(--text-secondary)]">{page.lead}</p>
        <div className="mt-10 space-y-4">
          {page.items.map((item) => <div key={item} className="flex gap-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 text-sm leading-6 text-[var(--text-secondary)]"><HiOutlineShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300" />{item}</div>)}
        </div>
        <Link to="/chat" className="mt-8 inline-flex h-11 items-center gap-2 rounded-lg bg-[var(--text-primary)] px-5 text-sm font-semibold text-[var(--bg-primary)]">Mở chatbot <HiOutlineArrowRight className="h-4 w-4" /></Link>
      </section>
    </main>
  );
}
