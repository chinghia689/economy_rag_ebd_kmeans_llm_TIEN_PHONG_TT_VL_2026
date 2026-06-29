import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import {
  HiOutlineArrowPath,
  HiOutlineBanknotes,
  HiOutlineBolt,
  HiOutlineChartBarSquare,
  HiOutlineCheckCircle,
  HiOutlineCircleStack,
  HiOutlineCog6Tooth,
  HiOutlineCommandLine,
  HiOutlineDocumentText,
  HiOutlineExclamationTriangle,
  HiOutlineMagnifyingGlass,
  HiOutlineServerStack,
  HiOutlineShieldCheck,
  HiOutlineUsers,
  HiOutlineArrowDownTray,
  HiOutlineTrash,
} from 'react-icons/hi2';
import {
  adminPasswordLogin,
  deleteAdminUser,
  getAdminSettings,
  getAdminSummary,
  downloadAdminTransactionsCsv,
  getAdminUserDetail,
  getAdminUsers,
  getDatabaseTables,
  getErrorMessage,
  runReadOnlySql,
  topUpUserTokens,
  updateAdminSetting,
  updateUserAdminRole,
} from '../../../services/api';
import type { AdminAuditLog, AdminDailyMetric, AdminSetting, AdminSummaryData, AdminUser, AdminUserDetailData, DatabaseTableInfo, SqlQueryData } from '../../../types';
import { useAuthStore } from '../../auth/authStore';
import PublicContentEditor from '../components/PublicContentEditor';

interface AdminPageProps {
  onOpenLogin: () => void;
  onPublicContentUpdated: () => void | Promise<void>;
}

const PUBLIC_CONTENT_KEYS = [
  'PUBLIC_PRIVACY_TITLE',
  'PUBLIC_PRIVACY_CONTENT',
  'PUBLIC_TERMS_TITLE',
  'PUBLIC_TERMS_CONTENT',
  'PUBLIC_SUPPORT_TITLE',
  'PUBLIC_SUPPORT_CONTENT',
  'PUBLIC_SUPPORT_EMAIL',
];
const PUBLIC_CONTENT_KEY_SET = new Set<string>(PUBLIC_CONTENT_KEYS);

function formatNumber(value: number | undefined) {
  return new Intl.NumberFormat('vi-VN').format(value || 0);
}

function formatVnd(value: number | undefined) {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value || 0);
}

function formatDate(value?: string) {
  if (!value) return '-';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('vi-VN');
}

function formatShortDate(value?: string) {
  if (!value) return '-';
  const normalized = value.includes('T') ? value : `${value}T00:00:00`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function buildEmptyDailyMetrics(days: number): AdminDailyMetric[] {
  const safeDays = Math.min(Math.max(Number(days) || 14, 1), 90);
  const today = new Date();

  return Array.from({ length: safeDays }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (safeDays - index - 1));
    const isoDate = date.toISOString().slice(0, 10);
    return {
      date: isoDate,
      revenue_vnd: 0,
      payment_tokens: 0,
      manual_tokens: 0,
      spent_tokens: 0,
      completed_payments: 0,
      questions: 0,
      active_users: 0,
    };
  });
}

function settingGroup(key: string) {
  if (key.startsWith('ADMIN_LOGIN')) return 'Admin';
  if (['ENV', 'PORT', 'ALLOW_ORIGINS', 'JWT_SECRET_KEY', 'DEFAULT_FREE_TOKENS', 'MAX_QUESTION_CHARS', 'TASK_RESULT_TTL_SECONDS', 'TASK_PROCESSING_TIMEOUT_SECONDS', 'TASK_CLEANUP_INTERVAL_SECONDS'].includes(key)) return 'Hệ thống';
  if (key === 'KEY_API_OPENAI' || key === 'OPENAI_LLM_MODEL_NAME' || key === 'LLM_TEMPERATURE') return 'OpenAI';
  if (key.includes('SEPAY') || key.includes('BANK') || key === 'NAME_WEB') return 'Thanh toán';
  if (key.includes('CLIENT') || key.includes('OAUTH')) return 'Đăng nhập';
  return 'Khác';
}

function settingDisplayKey(key: string) {
  if (key === 'DEFAULT_FREE_TOKENS') return 'DEFAULT_FREE_CREDITS';
  if (key === 'ADMIN_LOGIN_EMAIL') return 'ADMIN_LOGIN_ACCOUNT';
  return key;
}

function settingDisplayDescription(setting: AdminSetting) {
  if (setting.key === 'ADMIN_LOGIN_EMAIL') {
    return 'Tài khoản root admin. Chỉ root admin hiện tại được thay đổi.';
  }
  if (setting.key === 'ADMIN_LOGIN_PASSWORD') {
    return 'Mật khẩu root admin được lưu dạng hash. Chỉ root admin hiện tại được thay đổi.';
  }
  return setting.description;
}

function formatTransactionReason(reason: string, relatedPaymentId?: number | null) {
  if (reason === 'payment') return relatedPaymentId ? `Thanh toán #${relatedPaymentId}` : 'Thanh toán';
  if (reason.startsWith('admin_topup:')) {
    const parts = reason.split(':');
    const note = parts.slice(2).join(':');
    return note || 'Nạp thủ công';
  }
  if (reason.startsWith('chat:') || reason.startsWith('async_chat:')) return 'Sử dụng chat';
  return reason || 'Giao dịch credit';
}

function auditActionLabel(action: string) {
  const labels: Record<string, string> = {
    'admin.password_login': 'Đăng nhập admin',
    'user.admin_role.updated': 'Đổi quyền admin',
    'user.tokens.credited': 'Nạp credit',
    'user.account.self_deleted': 'Người dùng xóa tài khoản',
    'user.account.deleted_by_admin': 'Admin xóa tài khoản',
    'setting.updated': 'Đổi cấu hình',
    'settings.bulk_updated': 'Đổi nhiều cấu hình',
    'database.query.ran': 'Chạy SQL viewer',
  };
  return labels[action] || action;
}

function formatAuditDetails(log: AdminAuditLog) {
  const entries = Object.entries(log.details || {}).filter(([key]) => key !== 'query');
  if (entries.length === 0) return log.target_id || log.target_type || 'Không có chi tiết';
  return entries
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ');
}

function StatCard({ icon, label, value, detail, tone }: { icon: ReactNode; label: string; value: string; detail: string; tone: string }) {
  return (
    <article className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${tone}`}>
          {icon}
        </div>
        <span className="rounded-lg border border-[var(--border-color)] px-2 py-1 text-[11px] text-[var(--text-muted)]">Live</span>
      </div>
      <p className="mt-5 text-sm text-[var(--text-secondary)]">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-normal">{value}</p>
      <p className="mt-2 text-xs leading-5 text-[var(--text-muted)]">{detail}</p>
    </article>
  );
}

function MiniLineChart({
  title,
  metrics,
  getValue,
  formatValue,
  color,
}: {
  title: string;
  metrics: AdminDailyMetric[];
  getValue: (metric: AdminDailyMetric) => number;
  formatValue: (value: number) => string;
  color: string;
}) {
  const width = 320;
  const height = 150;
  const top = 16;
  const right = 12;
  const bottom = 34;
  const left = 14;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const baselineY = top + plotHeight;
  const values = metrics.map(getValue);
  const maxValue = Math.max(1, ...values);
  const total = values.reduce((sum, value) => sum + value, 0);

  const points = metrics.map((metric, index) => {
    const x = metrics.length <= 1 ? left + plotWidth / 2 : left + (index / (metrics.length - 1)) * plotWidth;
    const y = baselineY - (getValue(metric) / maxValue) * plotHeight;
    return { x, y, metric, value: getValue(metric) };
  });

  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
  const areaPath = points.length > 0
    ? `M ${points[0].x.toFixed(1)} ${baselineY} ${points.map((point) => `L ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ')} L ${points[points.length - 1].x.toFixed(1)} ${baselineY} Z`
    : '';
  const labelStep = Math.max(1, Math.ceil(metrics.length / 6));

  return (
    <div className="min-w-0">
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
        <span className="text-xs text-[var(--text-muted)]">Tổng {formatValue(total)}</span>
      </div>
      <div className="relative mt-4 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-2 py-3">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-40 w-full overflow-visible" role="img" aria-label={`Biểu đồ ${title}`}>
          {[0, 0.5, 1].map((ratio) => {
            const y = top + plotHeight * ratio;
            return <line key={ratio} x1={left} y1={y} x2={width - right} y2={y} stroke="currentColor" className="text-[var(--border-color)]" strokeWidth="1" />;
          })}
          <line x1={left} y1={baselineY} x2={width - right} y2={baselineY} stroke="currentColor" className="text-[var(--text-muted)]" strokeWidth="1" />
          {areaPath && <path d={areaPath} fill={color} opacity="0.12" />}
          {linePath && (
            <path
              d={linePath}
              fill="none"
              stroke={color}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
          {points.map((point, index) => (
            <g key={`${title}-${point.metric.date}`}>
              <circle cx={point.x} cy={point.y} r={point.value > 0 ? 3.8 : 2.8} fill="var(--bg-primary)" stroke={color} strokeWidth="2">
                <title>{`${formatShortDate(point.metric.date)} · ${formatValue(point.value)}`}</title>
              </circle>
              {(index === 0 || index === points.length - 1 || index % labelStep === 0) && (
                <text x={point.x} y={height - 10} textAnchor="middle" className="fill-[var(--text-muted)] text-[10px]">
                  {formatShortDate(point.metric.date)}
                </text>
              )}
            </g>
          ))}
        </svg>
        {total === 0 && (
          <div className="pointer-events-none absolute right-3 top-3 rounded-lg border border-dashed border-[var(--border-color)] bg-[var(--bg-secondary)]/85 px-3 py-1.5 text-xs text-[var(--text-muted)]">
            Đường đang ở mức 0
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminPage({ onOpenLogin, onPublicContentUpdated }: AdminPageProps) {
  const { user, isAuthenticated, isLoading, login, refreshBalance } = useAuthStore();
  const [summary, setSummary] = useState<AdminSummaryData | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [settings, setSettings] = useState<AdminSetting[]>([]);
  const [search, setSearch] = useState('');
  const [selectedEmail, setSelectedEmail] = useState('');
  const [topUpTokens, setTopUpTokens] = useState(100);
  const [topUpReason, setTopUpReason] = useState('Nạp credit thủ công');
  const [settingDrafts, setSettingDrafts] = useState<Record<string, string>>({});
  const [adminEmail, setAdminEmail] = useState('admin');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminLoginLoading, setAdminLoginLoading] = useState(false);
  const [dbTables, setDbTables] = useState<DatabaseTableInfo[]>([]);
  const [sqlQuery, setSqlQuery] = useState("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name");
  const [sqlResult, setSqlResult] = useState<SqlQueryData | null>(null);
  const [sqlLoading, setSqlLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [roleUpdatingEmail, setRoleUpdatingEmail] = useState<string | null>(null);
  const [deletingEmail, setDeletingEmail] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [dateRangeDays, setDateRangeDays] = useState(14);
  const [userDetail, setUserDetail] = useState<AdminUserDetailData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const canAdmin = Boolean(isAuthenticated && user?.is_admin);

  const loadAdminData = useCallback(async (nextSearch = search) => {
    if (!canAdmin) return;
    setLoading(true);
    setError('');
    try {
      const [summaryRes, usersRes, settingsRes, tablesRes] = await Promise.all([
        getAdminSummary(dateRangeDays),
        getAdminUsers(nextSearch),
        getAdminSettings(),
        getDatabaseTables(),
      ]);
      setSummary(summaryRes.data || null);
      const nextUsers = usersRes.data?.users || [];
      setUsers(nextUsers);
      setUserTotal(usersRes.data?.total || nextUsers.length);
      if (!selectedEmail && nextUsers[0]) {
        setSelectedEmail(nextUsers[0].email);
      }
      const nextSettings = settingsRes.data?.settings || [];
      setSettings(nextSettings);
      setDbTables(tablesRes.data?.tables || []);
      const drafts: Record<string, string> = {};
      nextSettings.forEach((setting) => {
        drafts[setting.key] = setting.is_secret ? '' : setting.value;
      });
      setSettingDrafts(drafts);
    } catch (err) {
      setError(getErrorMessage(err, 'Không tải được dữ liệu admin.'));
    } finally {
      setLoading(false);
    }
  }, [canAdmin, search, selectedEmail, dateRangeDays]);

  useEffect(() => {
    void loadAdminData();
  }, [loadAdminData]);

  const selectedUser = useMemo(
    () => users.find((item) => item.email === selectedEmail),
    [selectedEmail, users]
  );

  useEffect(() => {
    if (!canAdmin || !selectedEmail) {
      setUserDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    getAdminUserDetail(selectedEmail)
      .then((res) => {
        if (!cancelled) setUserDetail(res.data || null);
      })
      .catch(() => {
        if (!cancelled) setUserDetail(null);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [canAdmin, selectedEmail]);

  const dailyMetrics = summary?.daily_metrics?.length ? summary.daily_metrics : buildEmptyDailyMetrics(dateRangeDays);
  const auditLogs = summary?.recent_audit_logs || [];
  const latestMetric = dailyMetrics[dailyMetrics.length - 1];
  const alerts = summary?.alerts || [];
  const runtimeSettings = settings.filter((setting) => !PUBLIC_CONTENT_KEY_SET.has(setting.key));

  async function handleAdminPasswordLogin(event: FormEvent) {
    event.preventDefault();
    setAdminLoginLoading(true);
    setError('');
    setMessage('');
    try {
      const res = await adminPasswordLogin(adminEmail, adminPassword);
      if (res.success && res.data?.token && res.data.user) {
        await login(res.data.token, res.data.user);
        setMessage('Đăng nhập admin thành công.');
        setAdminPassword('');
      }
    } catch (err) {
      setError(getErrorMessage(err, 'Không đăng nhập được admin.'));
    } finally {
      setAdminLoginLoading(false);
    }
  }

  async function handleRunSql(event: FormEvent) {
    event.preventDefault();
    setSqlLoading(true);
    setError('');
    try {
      const res = await runReadOnlySql(sqlQuery, 100);
      setSqlResult(res.data || null);
      await loadAdminData(search);
    } catch (err) {
      setError(getErrorMessage(err, 'Không chạy được SQL.'));
    } finally {
      setSqlLoading(false);
    }
  }

  async function handleSearchSubmit(event: FormEvent) {
    event.preventDefault();
    await loadAdminData(search);
  }

  async function handleDownloadCsv() {
    setCsvLoading(true);
    setError('');
    setMessage('');
    try {
      const blob = await downloadAdminTransactionsCsv();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `credit-transactions-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage('Đã tải CSV giao dịch.');
    } catch (err) {
      setError(getErrorMessage(err, 'Không tải được CSV.'));
    } finally {
      setCsvLoading(false);
    }
  }

  async function handleAdminRoleChange(targetEmail: string, nextIsAdmin: boolean) {
    setRoleUpdatingEmail(targetEmail);
    setMessage('');
    setError('');
    try {
      await updateUserAdminRole(targetEmail, nextIsAdmin);
      setMessage(nextIsAdmin ? `Đã cấp quyền admin cho ${targetEmail}.` : `Đã gỡ quyền admin của ${targetEmail}.`);
      await loadAdminData(search);
    } catch (err) {
      setError(getErrorMessage(err, 'Không cập nhật được quyền admin.'));
    } finally {
      setRoleUpdatingEmail(null);
    }
  }

  async function handleDeleteUser(targetEmail: string) {
    const confirmed = window.confirm(
      `Xóa vĩnh viễn tài khoản ${targetEmail}? Toàn bộ dữ liệu sẽ bị xóa và email này không thể đăng nhập lại.`,
    );
    if (!confirmed) return;

    setDeletingEmail(targetEmail);
    setMessage('');
    setError('');
    try {
      await deleteAdminUser(targetEmail);
      if (selectedEmail === targetEmail) {
        setSelectedEmail('');
        setUserDetail(null);
      }
      setMessage(`Đã xóa ${targetEmail} và chặn email đăng nhập lại.`);
      await loadAdminData(search);
    } catch (err) {
      setError(getErrorMessage(err, 'Không xóa được tài khoản.'));
    } finally {
      setDeletingEmail(null);
    }
  }

  async function handleTopUp(event: FormEvent) {
    event.preventDefault();
    if (!selectedEmail) return;
    setMessage('');
    setError('');
    try {
      await topUpUserTokens(selectedEmail, topUpTokens, topUpReason);
      setMessage(`Đã nạp ${formatNumber(topUpTokens)} credit cho ${selectedEmail}.`);
      await loadAdminData(search);
      await refreshBalance().catch(() => undefined);
    } catch (err) {
      setError(getErrorMessage(err, 'Không nạp được credit.'));
    }
  }

  async function handleSaveSetting(setting: AdminSetting) {
    const value = settingDrafts[setting.key] ?? '';
    if (setting.is_secret && !value.trim()) {
      setError('Nhập giá trị mới trước khi lưu secret.');
      return;
    }
    setSavingKey(setting.key);
    setMessage('');
    setError('');
    try {
      await updateAdminSetting(setting.key, value);
      setMessage(`Đã cập nhật ${setting.key}.`);
      await loadAdminData(search);
    } catch (err) {
      setError(getErrorMessage(err, 'Không cập nhật được cấu hình.'));
    } finally {
      setSavingKey(null);
    }
  }

  async function handleSavePublicContent() {
    const requiredKeys = PUBLIC_CONTENT_KEYS.filter((key) => key !== 'PUBLIC_SUPPORT_EMAIL');
    if (requiredKeys.some((key) => !(settingDrafts[key] ?? '').trim())) {
      setError('Tiêu đề và nội dung chính sách, điều khoản, hỗ trợ không được để trống.');
      return;
    }

    setSavingKey('PUBLIC_CONTENT');
    setMessage('');
    setError('');
    try {
      for (const key of PUBLIC_CONTENT_KEYS) {
        await updateAdminSetting(key, settingDrafts[key] ?? '');
      }
      await loadAdminData(search);
      await onPublicContentUpdated();
      setMessage('Đã cập nhật chính sách bảo mật, điều khoản sử dụng và thông tin hỗ trợ.');
    } catch (err) {
      setError(getErrorMessage(err, 'Không cập nhật được nội dung công khai.'));
    } finally {
      setSavingKey(null);
    }
  }

  if (isLoading) {
    return (
      <main className="flex min-h-[calc(100dvh-4rem)] items-center justify-center bg-[var(--bg-primary)] text-[var(--text-secondary)]">
        Đang kiểm tra phiên đăng nhập...
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="flex min-h-[calc(100dvh-4rem)] items-center justify-center bg-[var(--bg-primary)] px-4 py-10 text-[var(--text-primary)]">
        <section className="w-full max-w-md rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6">
          <HiOutlineExclamationTriangle className="h-8 w-8 text-amber-300" />
          <h1 className="mt-4 text-xl font-semibold">Đăng nhập admin</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
            Dùng tài khoản admin và mật khẩu cố định đã cấu hình trong DB.
          </p>

          {error && (
            <div className="mt-4 rounded-lg border border-red-500/35 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          )}

          <form onSubmit={handleAdminPasswordLogin} className="mt-5 space-y-4">
            <label className="block text-sm text-[var(--text-secondary)]">
              Tài khoản admin
              <input
                type="text"
                value={adminEmail}
                onChange={(event) => setAdminEmail(event.target.value)}
                autoComplete="username"
                className="mt-2 h-10 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]"
              />
            </label>
            <label className="block text-sm text-[var(--text-secondary)]">
              Mật khẩu
              <input
                type="password"
                autoComplete="current-password"
                value={adminPassword}
                onChange={(event) => setAdminPassword(event.target.value)}
                className="mt-2 h-10 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]"
              />
            </label>
            <button
              disabled={adminLoginLoading}
              className="h-10 w-full rounded-lg bg-[var(--text-primary)] px-4 text-sm font-semibold text-[var(--bg-primary)] transition-opacity disabled:opacity-50"
            >
              {adminLoginLoading ? 'Đang đăng nhập' : 'Đăng nhập admin'}
            </button>
          </form>

          <button
            onClick={onOpenLogin}
            className="mt-3 h-10 w-full rounded-lg border border-[var(--border-color)] px-4 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            Đăng nhập bằng Google
          </button>
        </section>
      </main>
    );
  }

  if (!user?.is_admin) {
    return (
      <main className="flex min-h-[calc(100dvh-4rem)] items-center justify-center bg-[var(--bg-primary)] px-4 text-[var(--text-primary)]">
        <section className="w-full max-w-md rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 text-center">
          <HiOutlineExclamationTriangle className="mx-auto h-8 w-8 text-red-300" />
          <h1 className="mt-4 text-xl font-semibold">Không có quyền admin</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">Tài khoản hiện tại chưa được cấp quyền quản trị.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 border-b border-[var(--border-color)] pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Admin dashboard</p>
            <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Vận hành tài khoản, credit và cấu hình AI</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
              Theo dõi doanh thu, credit, hoạt động người dùng và các thay đổi nhạy cảm trong một màn hình quản trị.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {[1, 7, 14, 30].map((days) => (
              <button
                key={days}
                onClick={() => setDateRangeDays(days)}
                className={`h-10 rounded-lg border px-3 text-sm transition-colors ${dateRangeDays === days ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'}`}
              >
                {days === 1 ? 'Hôm nay' : `${days} ngày`}
              </button>
            ))}
            <button
              onClick={() => void handleDownloadCsv()}
              disabled={csvLoading}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] disabled:opacity-50"
            >
              <HiOutlineArrowDownTray className="h-4 w-4" /> {csvLoading ? 'Đang tải' : 'CSV'}
            </button>
            <button
              onClick={() => void loadAdminData(search)}
              className="inline-flex h-10 w-fit items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              <HiOutlineArrowPath className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Làm mới
            </button>
          </div>
        </div>

        {(message || error) && (
          <div className={`mt-5 flex items-start gap-3 rounded-lg border p-4 text-sm ${
            error
              ? 'border-red-500/35 bg-red-500/10 text-red-200'
              : 'border-emerald-500/35 bg-emerald-500/10 text-emerald-200'
          }`}>
            {error ? <HiOutlineExclamationTriangle className="mt-0.5 h-5 w-5" /> : <HiOutlineCheckCircle className="mt-0.5 h-5 w-5" />}
            <span>{error || message}</span>
          </div>
        )}

        {alerts.length > 0 && (
          <section className="mt-6 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
            <div className="flex items-center gap-2 text-amber-200">
              <HiOutlineExclamationTriangle className="h-5 w-5" />
              <h2 className="text-sm font-semibold">Cảnh báo vận hành</h2>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {alerts.map((alert) => (
                <div key={alert.code} className="rounded-lg border border-amber-500/20 bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                  <span className="font-semibold text-[var(--text-primary)]">{alert.code}</span> · {alert.message}
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={<HiOutlineUsers className="h-5 w-5 text-emerald-200" />}
            label="Tài khoản"
            value={formatNumber(summary?.total_users)}
            detail={`${formatNumber(latestMetric?.active_users)} active hôm nay`}
            tone="bg-emerald-500/15"
          />
          <StatCard
            icon={<HiOutlineCircleStack className="h-5 w-5 text-sky-200" />}
            label="Credit còn trong hệ thống"
            value={formatNumber(summary?.total_token_balance)}
            detail={`${formatNumber(summary?.spent_tokens)} credit đã sử dụng`}
            tone="bg-sky-500/15"
          />
          <StatCard
            icon={<HiOutlineBanknotes className="h-5 w-5 text-amber-200" />}
            label="Doanh thu đã khớp"
            value={formatVnd(summary?.completed_revenue_vnd)}
            detail={`${formatNumber(summary?.payment_tokens)} credit qua thanh toán`}
            tone="bg-amber-500/15"
          />
          <StatCard
            icon={<HiOutlineServerStack className="h-5 w-5 text-rose-200" />}
            label="Payment hoàn tất / chờ"
            value={`${formatNumber(summary?.completed_payments)} / ${formatNumber(summary?.pending_payments)}`}
            detail={`${formatNumber(summary?.total_payments)} payment đã tạo`}
            tone="bg-rose-500/15"
          />
        </section>

        <section className="mt-8 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
            <div className="flex items-center gap-2">
              <HiOutlineChartBarSquare className="h-5 w-5 text-[var(--text-secondary)]" />
              <h2 className="text-lg font-semibold">Biểu đồ {dateRangeDays === 1 ? 'hôm nay' : `${dateRangeDays} ngày`}</h2>
            </div>
            <div className="mt-5 grid gap-6 lg:grid-cols-2">
              <MiniLineChart
                title="Doanh thu"
                metrics={dailyMetrics}
                getValue={(metric) => metric.revenue_vnd}
                formatValue={formatVnd}
                color="#34d399"
              />
              <MiniLineChart
                title="Câu hỏi"
                metrics={dailyMetrics}
                getValue={(metric) => metric.questions}
                formatValue={formatNumber}
                color="#38bdf8"
              />
              <MiniLineChart
                title="Credit nạp thủ công"
                metrics={dailyMetrics}
                getValue={(metric) => metric.manual_tokens}
                formatValue={formatNumber}
                color="#fbbf24"
              />
              <MiniLineChart
                title="Credit sử dụng"
                metrics={dailyMetrics}
                getValue={(metric) => metric.spent_tokens}
                formatValue={formatNumber}
                color="#fb7185"
              />
              <MiniLineChart
                title="User active"
                metrics={dailyMetrics}
                getValue={(metric) => metric.active_users}
                formatValue={formatNumber}
                color="#5eead4"
              />
              <MiniLineChart
                title="Payment hoàn tất"
                metrics={dailyMetrics}
                getValue={(metric) => metric.completed_payments}
                formatValue={formatNumber}
                color="#a5b4fc"
              />
            </div>
          </div>

          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
            <div className="flex items-center gap-2">
              <HiOutlineShieldCheck className="h-5 w-5 text-[var(--text-secondary)]" />
              <h2 className="text-lg font-semibold">Audit log mới nhất</h2>
            </div>
            <div className="mt-5 space-y-3">
              {auditLogs.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[var(--border-color)] py-10 text-center text-sm text-[var(--text-muted)]">Chưa có audit log.</div>
              ) : auditLogs.map((log) => (
                <article key={log.id} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{auditActionLabel(log.action)}</p>
                      <p className="mt-1 truncate text-xs text-[var(--text-muted)]">{formatAuditDetails(log)}</p>
                    </div>
                    <span className="shrink-0 rounded-lg bg-[var(--bg-hover)] px-2 py-1 text-[10px] text-[var(--text-muted)]">#{log.id}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--text-muted)]">
                    <span>{log.actor_email}</span>
                    <span>{formatDate(log.created_at)}</span>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-6 xl:grid-cols-2">
          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
            <div className="flex items-center gap-2">
              <HiOutlineBolt className="h-5 w-5 text-[var(--text-secondary)]" />
              <h2 className="text-lg font-semibold">Credit ledger gần đây</h2>
            </div>
            <div className="mt-5 divide-y divide-[var(--border-color)]">
              {(summary?.recent_transactions || []).map((tx) => {
                const isCredit = tx.delta > 0;
                return (
                  <div key={tx.id} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{formatTransactionReason(tx.reason, tx.related_payment_id)}</p>
                      <p className="mt-1 text-xs text-[var(--text-muted)]">{tx.user_email} · {formatDate(tx.created_at)}</p>
                    </div>
                    <span className={`shrink-0 text-sm font-semibold ${isCredit ? 'text-emerald-300' : 'text-rose-300'}`}>{isCredit ? '+' : ''}{formatNumber(tx.delta)}</span>
                  </div>
                );
              })}
              {(!summary?.recent_transactions || summary.recent_transactions.length === 0) && (
                <div className="py-8 text-center text-sm text-[var(--text-muted)]">Chưa có giao dịch credit.</div>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
            <div className="flex items-center gap-2">
              <HiOutlineDocumentText className="h-5 w-5 text-[var(--text-secondary)]" />
              <h2 className="text-lg font-semibold">Payment gần đây</h2>
            </div>
            <div className="mt-5 divide-y divide-[var(--border-color)]">
              {(summary?.recent_payments || []).map((payment) => (
                <div key={payment.id} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">#{payment.id} · {payment.package_id || 'custom'}</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">{payment.user_email} · {formatDate(payment.created_at)}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-sm font-semibold">{formatVnd(payment.amount_vnd)}</p>
                    <p className={`mt-1 text-xs ${payment.status === 'completed' ? 'text-emerald-300' : 'text-amber-300'}`}>{payment.status}</p>
                  </div>
                </div>
              ))}
              {(!summary?.recent_payments || summary.recent_payments.length === 0) && (
                <div className="py-8 text-center text-sm text-[var(--text-muted)]">Chưa có payment.</div>
              )}
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
          <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]">
            <div className="flex flex-col gap-4 border-b border-[var(--border-color)] p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Tài khoản con</h2>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">{formatNumber(users.length)} / {formatNumber(userTotal)} tài khoản đang hiển thị</p>
              </div>
              <form onSubmit={handleSearchSubmit} className="flex w-full gap-2 md:w-80">
                <div className="relative flex-1">
                  <HiOutlineMagnifyingGlass className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    className="h-10 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] pl-9 pr-3 text-sm outline-none focus:border-[var(--accent-primary)]"
                    placeholder="Tìm email hoặc tên"
                  />
                </div>
                <button className="h-10 rounded-lg bg-[var(--text-primary)] px-4 text-sm font-semibold text-[var(--bg-primary)]">
                  Tìm
                </button>
              </form>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead className="border-b border-[var(--border-color)] text-xs uppercase tracking-[0.12em] text-[var(--text-muted)]">
                  <tr>
                    <th className="px-4 py-3 font-medium">Tài khoản</th>
                    <th className="px-4 py-3 font-medium">Credit</th>
                    <th className="px-4 py-3 font-medium">Thanh toán</th>
                    <th className="px-4 py-3 font-medium">Hội thoại</th>
                    <th className="px-4 py-3 font-medium">Quyền</th>
                    <th className="px-4 py-3 font-medium">Đăng nhập</th>
                    <th className="px-4 py-3 font-medium">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-color)]">
                  {users.map((item) => (
                    <tr key={item.email} className={selectedEmail === item.email ? 'bg-[var(--bg-hover)]/55' : ''}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {item.picture ? (
                            <img src={item.picture} alt={item.name || item.email} className="h-9 w-9 rounded-full border border-[var(--border-color)]" />
                          ) : (
                            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--bg-hover)] text-xs font-semibold">
                              {(item.name || item.email)[0]?.toUpperCase()}
                            </div>
                          )}
                          <div className="min-w-0">
                            <p className="truncate font-medium">{item.name || 'Chưa có tên'}</p>
                            <p className="truncate text-xs text-[var(--text-muted)]">{item.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-semibold">{formatNumber(item.token_balance)}</td>
                      <td className="px-4 py-3">{formatVnd(item.completed_revenue_vnd)}</td>
                      <td className="px-4 py-3">{formatNumber(item.conversation_count)} / {formatNumber(item.message_count)} tin</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex h-7 items-center rounded-lg px-2.5 text-xs font-semibold ${
                          item.is_admin
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : 'bg-[var(--bg-hover)] text-[var(--text-secondary)]'
                        }`}>
                          {item.is_admin ? 'Admin' : 'User'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[var(--text-secondary)]">{formatDate(item.last_login)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => setSelectedEmail(item.email)}
                            className="h-9 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                          >
                            Chọn nạp
                          </button>
                          <button
                            onClick={() => void handleAdminRoleChange(item.email, !item.is_admin)}
                            disabled={roleUpdatingEmail === item.email || (item.email === user?.email && item.is_admin)}
                            className={`h-9 rounded-lg border px-3 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${
                              item.is_admin
                                ? 'border-red-500/35 text-red-300 hover:bg-red-500/10'
                                : 'border-emerald-500/35 text-emerald-300 hover:bg-emerald-500/10'
                            }`}
                            title={item.email === user?.email && item.is_admin ? 'Không thể tự gỡ quyền admin của chính mình' : undefined}
                          >
                            {roleUpdatingEmail === item.email
                              ? 'Đang lưu'
                              : item.is_admin
                                ? 'Gỡ admin'
                                : 'Cấp admin'}
                          </button>
                          <button
                            onClick={() => void handleDeleteUser(item.email)}
                            disabled={deletingEmail === item.email || item.email === user?.email}
                            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-red-500/35 px-3 text-sm text-red-300 transition-colors hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-45"
                            title={item.email === user?.email ? 'Không thể tự xóa tài khoản admin đang đăng nhập' : 'Xóa vĩnh viễn và chặn email'}
                          >
                            <HiOutlineTrash className="h-4 w-4" />
                            {deletingEmail === item.email ? 'Đang xóa' : 'Xóa'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td className="px-4 py-10 text-center text-[var(--text-muted)]" colSpan={7}>Không có tài khoản phù hợp.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <form onSubmit={handleTopUp} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
            <h2 className="text-lg font-semibold">Nạp credit thủ công</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
              {selectedUser ? selectedUser.email : 'Chọn một tài khoản trong bảng để nạp credit.'}
            </p>
            <label className="mt-5 block text-sm text-[var(--text-secondary)]">
              Số credit
              <input
                type="number"
                min={1}
                max={10000000}
                value={topUpTokens}
                onChange={(event) => setTopUpTokens(Number(event.target.value))}
                className="mt-2 h-10 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]"
              />
            </label>
            <label className="mt-4 block text-sm text-[var(--text-secondary)]">
              Ghi chú
              <input
                value={topUpReason}
                onChange={(event) => setTopUpReason(event.target.value)}
                className="mt-2 h-10 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]"
              />
            </label>
            <button
              disabled={!selectedEmail}
              className="mt-5 h-10 w-full rounded-lg bg-[var(--text-primary)] px-4 text-sm font-semibold text-[var(--bg-primary)] transition-opacity disabled:cursor-not-allowed disabled:opacity-45"
            >
              Nạp credit
            </button>
          </form>
        </section>

        <section className="mt-8 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]">
          <div className="border-b border-[var(--border-color)] p-4">
            <div className="flex items-center gap-2">
              <HiOutlineUsers className="h-5 w-5 text-[var(--text-secondary)]" />
              <h2 className="text-lg font-semibold">User detail</h2>
            </div>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">Credit, payment, hội thoại và quyền của tài khoản đang chọn.</p>
          </div>
          <div className="grid gap-6 p-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
              {detailLoading ? (
                <p className="text-sm text-[var(--text-muted)]">Đang tải chi tiết...</p>
              ) : userDetail ? (
                <div>
                  <p className="text-sm font-semibold">{userDetail.user.name || 'Chưa có tên'}</p>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">{userDetail.user.email}</p>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-muted)]">Credit</p><p className="mt-1 font-semibold">{formatNumber(userDetail.user.token_balance)}</p></div>
                    <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-muted)]">Quyền</p><p className="mt-1 font-semibold">{userDetail.user.is_admin ? 'Admin' : 'User'}</p></div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-[var(--text-muted)]">Chọn một tài khoản để xem chi tiết.</p>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                <h3 className="text-sm font-semibold">Credit history</h3>
                <div className="mt-3 space-y-2 text-xs text-[var(--text-secondary)]">
                  {(userDetail?.transactions || []).slice(0, 5).map((tx) => <p key={tx.id} className="truncate">{tx.delta > 0 ? '+' : ''}{formatNumber(tx.delta)} · {formatTransactionReason(tx.reason, tx.related_payment_id)}</p>)}
                  {(!userDetail?.transactions || userDetail.transactions.length === 0) && <p className="text-[var(--text-muted)]">Chưa có giao dịch.</p>}
                </div>
              </div>
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                <h3 className="text-sm font-semibold">Payments</h3>
                <div className="mt-3 space-y-2 text-xs text-[var(--text-secondary)]">
                  {(userDetail?.payments || []).slice(0, 5).map((payment) => <p key={payment.id} className="truncate">#{payment.id} · {payment.status} · {formatVnd(payment.amount_vnd)}</p>)}
                  {(!userDetail?.payments || userDetail.payments.length === 0) && <p className="text-[var(--text-muted)]">Chưa có payment.</p>}
                </div>
              </div>
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                <h3 className="text-sm font-semibold">Conversations</h3>
                <div className="mt-3 space-y-2 text-xs text-[var(--text-secondary)]">
                  {(userDetail?.conversations || []).slice(0, 5).map((conv) => <p key={conv.id} className="truncate">{conv.title}</p>)}
                  {(!userDetail?.conversations || userDetail.conversations.length === 0) && <p className="text-[var(--text-muted)]">Chưa có hội thoại.</p>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <PublicContentEditor
          values={settingDrafts}
          isSaving={savingKey === 'PUBLIC_CONTENT'}
          onChange={(key, value) => setSettingDrafts((current) => ({ ...current, [key]: value }))}
          onSave={() => void handleSavePublicContent()}
        />


        <section className="mt-8 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]">
          <div className="border-b border-[var(--border-color)] p-4">
            <div className="flex items-center gap-2">
              <HiOutlineCog6Tooth className="h-5 w-5 text-[var(--text-secondary)]" />
              <h2 className="text-lg font-semibold">Cấu hình API và SePay</h2>
            </div>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">Secret chỉ hiển thị dạng mask. Nhập giá trị mới để thay thế.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] text-left text-sm">
              <thead className="border-b border-[var(--border-color)] text-xs uppercase tracking-[0.12em] text-[var(--text-muted)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Nhóm</th>
                  <th className="px-4 py-3 font-medium">Key</th>
                  <th className="px-4 py-3 font-medium">Giá trị</th>
                  <th className="px-4 py-3 font-medium">Mô tả</th>
                  <th className="px-4 py-3 font-medium">Lưu</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]">
                {runtimeSettings.map((setting) => (
                  <tr key={setting.key}>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{settingGroup(setting.key)}</td>
                    <td className="px-4 py-3 font-mono text-xs">{settingDisplayKey(setting.key)}</td>
                    <td className="px-4 py-3">
                      <input
                        type={setting.is_secret ? 'password' : 'text'}
                        value={settingDrafts[setting.key] ?? ''}
                        onChange={(event) => setSettingDrafts((current) => ({ ...current, [setting.key]: event.target.value }))}
                        placeholder={setting.is_secret ? setting.value_preview || 'Nhập secret mới' : 'Nhập giá trị'}
                        className="h-10 w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]"
                      />
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{settingDisplayDescription(setting)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => void handleSaveSetting(setting)}
                        disabled={savingKey === setting.key}
                        className="h-9 rounded-lg border border-[var(--border-color)] px-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] disabled:opacity-50"
                      >
                        {savingKey === setting.key ? 'Đang lưu' : 'Lưu'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-8 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]">
          <div className="border-b border-[var(--border-color)] p-4">
            <div className="flex items-center gap-2">
              <HiOutlineCommandLine className="h-5 w-5 text-[var(--text-secondary)]" />
              <h2 className="text-lg font-semibold">SQL viewer</h2>
            </div>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Chỉ cho phép SELECT hoặc PRAGMA. Query raw `app_settings` bị chặn để tránh lộ secret API key.
            </p>
          </div>

          <div className="grid gap-6 p-4 lg:grid-cols-[0.65fr_1.35fr]">
            <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)]">
              <div className="border-b border-[var(--border-color)] px-4 py-3 text-sm font-semibold">Tables</div>
              <div className="max-h-96 overflow-y-auto p-2">
                {dbTables.map((table) => (
                  <details key={table.name} className="rounded-lg px-2 py-2 text-sm open:bg-[var(--bg-hover)]/50">
                    <summary className="cursor-pointer font-mono text-xs text-[var(--text-primary)]">
                      {table.name} <span className="text-[var(--text-muted)]">({formatNumber(table.row_count)})</span>
                    </summary>
                    <div className="mt-2 space-y-1 pl-3">
                      {table.columns.map((column) => (
                        <button
                          key={`${table.name}.${column.name}`}
                          onClick={() => setSqlQuery(`SELECT * FROM ${table.name} LIMIT 100`)}
                          className="block w-full rounded px-2 py-1 text-left font-mono text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-primary)] hover:text-[var(--text-primary)]"
                        >
                          {column.name} <span className="text-[var(--text-muted)]">{column.type || 'ANY'}</span>
                        </button>
                      ))}
                    </div>
                  </details>
                ))}
              </div>
            </div>

            <form onSubmit={handleRunSql} className="min-w-0 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)]">
              <div className="border-b border-[var(--border-color)] p-3">
                <textarea
                  value={sqlQuery}
                  onChange={(event) => setSqlQuery(event.target.value)}
                  className="h-28 w-full resize-y rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-3 font-mono text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-primary)]"
                  spellCheck={false}
                />
                <button
                  disabled={sqlLoading}
                  className="mt-3 h-10 rounded-lg bg-[var(--text-primary)] px-4 text-sm font-semibold text-[var(--bg-primary)] transition-opacity disabled:opacity-50"
                >
                  {sqlLoading ? 'Đang chạy' : 'Chạy SQL'}
                </button>
              </div>

              <div className="max-h-[30rem] overflow-auto p-3">
                {sqlResult ? (
                  <table className="w-full min-w-[640px] text-left text-xs">
                    <thead className="border-b border-[var(--border-color)] text-[var(--text-muted)]">
                      <tr>
                        {sqlResult.columns.map((column) => (
                          <th key={column} className="px-3 py-2 font-mono font-medium">{column}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-color)]">
                      {sqlResult.rows.map((row, rowIndex) => (
                        <tr key={rowIndex}>
                          {sqlResult.columns.map((column) => (
                            <td key={column} className="max-w-xs truncate px-3 py-2 font-mono text-[var(--text-secondary)]" title={String(row[column] ?? '')}>
                              {String(row[column] ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                      {sqlResult.rows.length === 0 && (
                        <tr>
                          <td className="px-3 py-8 text-center text-[var(--text-muted)]" colSpan={Math.max(sqlResult.columns.length, 1)}>
                            Không có dòng dữ liệu.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                ) : (
                  <div className="py-12 text-center text-sm text-[var(--text-muted)]">Chạy một query để xem kết quả.</div>
                )}
              </div>
            </form>
          </div>
        </section>
      </div>
    </main>
  );
}
