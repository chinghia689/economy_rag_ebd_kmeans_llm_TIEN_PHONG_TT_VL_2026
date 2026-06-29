import { HiOutlineArrowRight, HiOutlineBanknotes, HiOutlineShieldCheck } from 'react-icons/hi2';

interface PricingPageProps {
  onOpenPayment: () => void;
}

const packages = [
  { name: 'Starter', id: 'basic', questions: '100 câu hỏi', price: '30.000đ', unit: '300đ/câu' },
  { name: 'Research', id: 'pro', questions: '500 câu hỏi', price: '120.000đ', unit: '240đ/câu' },
  { name: 'Team', id: 'premium', questions: '1.200 câu hỏi', price: '250.000đ', unit: '208đ/câu' },
];

const facts = [
  '1 câu hỏi thường trừ 1 credit.',
  'Thanh toán qua SePay/VietQR, cần chuyển đúng số tiền và nội dung.',
  'Giao dịch khớp sẽ cộng credit và ghi vào lịch sử giao dịch.',
];

export default function PricingPage({ onOpenPayment }: PricingPageProps) {
  return (
    <main className="min-h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <section className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <div className="max-w-3xl">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Pricing</p>
          <h1 className="mt-4 text-5xl font-semibold leading-tight">Nạp credit theo số câu hỏi.</h1>
          <p className="mt-5 text-base leading-7 text-[var(--text-secondary)]">
            Gói Starter 30.000đ nhận 100 credit, tương đương khoảng 100 câu hỏi thường.
          </p>
        </div>

        <div className="mt-10 grid gap-4 lg:grid-cols-3">
          {packages.map((pkg) => (
            <article key={pkg.id} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6">
              <HiOutlineBanknotes className="h-6 w-6 text-emerald-300" />
              <h2 className="mt-5 text-2xl font-semibold">{pkg.name}</h2>
              <p className="mt-6 text-4xl font-semibold">{pkg.price}</p>
              <p className="mt-2 text-lg font-medium text-[var(--text-primary)]">{pkg.questions}</p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">{pkg.unit}</p>
              <button onClick={onOpenPayment} className="mt-7 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[var(--text-primary)] px-4 text-sm font-semibold text-[var(--bg-primary)] transition-opacity hover:opacity-90">
                Nạp credit <HiOutlineArrowRight className="h-4 w-4" />
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="border-t border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <h2 className="text-lg font-semibold">Thông tin đang áp dụng</h2>
          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            {facts.map((item) => (
              <div key={item} className="flex gap-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4 text-sm leading-6 text-[var(--text-secondary)]">
                <HiOutlineShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300" />
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
