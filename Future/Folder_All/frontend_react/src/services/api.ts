import type {
  AdminAuditLogsData,
  AdminLoginData,
  AdminSettingsData,
  AdminSummaryData,
  AdminTopUpData,
  AdminUser,
  AdminUserDetailData,
  AdminUsersData,
  ApiResponse,
  DatabaseTablesData,
  ChatHistoryData,
  ChatResponseData,
  ClearChatHistoryData,
  ConversationData,
  ConversationListData,
  ConversationMessagesData,
  HealthData,
  LoginSessionCreateData,
  LoginSessionPollData,
  PaymentCreateData,
  PaymentStatusData,
  PublicContentData,
  SqlQueryData,
  TokenBalanceData,
  User,
  VerifyTokenData,
} from '../types';

const API_BASE = '/api';

/**
 * Helper: thêm Authorization header nếu có token
 */
function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/**
 * Generic fetch wrapper
 */
function readObject(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null
    ? value as Record<string, unknown>
    : null;
}

function apiErrorMessage(data: unknown, fallback: string): string {
  const root = readObject(data);
  if (!root) return fallback;

  if (typeof root.message === 'string') {
    return root.message;
  }

  const detail = readObject(root.detail);
  if (detail && typeof detail.message === 'string') {
    return detail.message;
  }

  return fallback;
}

export function getErrorMessage(error: unknown, fallback = 'Lỗi không xác định.'): string {
  return error instanceof Error ? error.message : fallback;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...options.headers,
    },
  });

  const data: unknown = await res.json();

  if (!res.ok) {
    throw new Error(apiErrorMessage(data, `HTTP ${res.status}`));
  }

  return data as T;
}

/* ─────────────────────── Chat API ─────────────────────── */

export async function sendChatMessage(question: string) {
  return request<ApiResponse<ChatResponseData>>(`${API_BASE}/chat`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

export async function listConversations() {
  return request<ApiResponse<ConversationListData>>(`${API_BASE}/v1/chat/conversations`);
}

export async function createConversation(title?: string) {
  return request<ApiResponse<ConversationData>>(`${API_BASE}/v1/chat/conversations`, {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function getConversationMessages(conversationId: string) {
  return request<ApiResponse<ConversationMessagesData>>(
    `${API_BASE}/v1/chat/conversations/${conversationId}/messages`
  );
}

export async function sendConversationMessage(conversationId: string, question: string) {
  return request<ApiResponse<ChatResponseData>>(
    `${API_BASE}/v1/chat/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({ question }),
    }
  );
}

export async function updateConversationTitle(conversationId: string, title: string) {
  return request<ApiResponse<ConversationData>>(`${API_BASE}/v1/chat/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(conversationId: string) {
  return request<ApiResponse<{ deleted: boolean }>>(`${API_BASE}/v1/chat/conversations/${conversationId}`, {
    method: 'DELETE',
  });
}

export async function getChatHistory(limit = 100, offset = 0) {
  return request<ApiResponse<ChatHistoryData>>(`${API_BASE}/chat/history?limit=${limit}&offset=${offset}`);
}

export async function clearChatHistory() {
  return request<ApiResponse<ClearChatHistoryData>>(`${API_BASE}/chat/history`, {
    method: 'DELETE',
  });
}

/* ─────────────────────── Health API ─────────────────────── */

export async function checkHealth() {
  return request<ApiResponse<HealthData>>(`${API_BASE}/health`);
}

/* ─────────────────────── Public Content API ─────────────────────── */

export async function getPublicContent() {
  return request<ApiResponse<PublicContentData>>(`${API_BASE}/v1/public/content`);
}

/* ─────────────────────── Auth API ─────────────────────── */

export async function createLoginSession(sessionId: string) {
  const formData = new URLSearchParams();
  formData.append('session_id', sessionId);

  const res = await fetch(`${API_BASE}/v1/auth/login-session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });
  const data: unknown = await res.json();
  if (!res.ok) {
    throw new Error(apiErrorMessage(data, `HTTP ${res.status}`));
  }
  return data as ApiResponse<LoginSessionCreateData>;
}

export async function pollLoginSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/v1/auth/login-session/${sessionId}`);
  const data: unknown = await res.json();
  if (!res.ok) {
    throw new Error(apiErrorMessage(data, `HTTP ${res.status}`));
  }
  return data as LoginSessionPollData;
}

export async function verifyToken(token: string) {
  const formData = new URLSearchParams();
  formData.append('token', token);

  const res = await fetch(`${API_BASE}/v1/auth/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });
  const data: unknown = await res.json();
  if (!res.ok) {
    throw new Error(apiErrorMessage(data, `HTTP ${res.status}`));
  }
  return data as ApiResponse<VerifyTokenData>;
}


export async function adminPasswordLogin(email: string, password: string) {
  return request<ApiResponse<AdminLoginData>>(`${API_BASE}/v1/auth/admin/login`, {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe() {
  return request<ApiResponse<User>>(`${API_BASE}/v1/auth/me`);
}

export async function getBalance() {
  return request<ApiResponse<TokenBalanceData>>(`${API_BASE}/v1/me/balance`);
}

export async function deleteMyAccount(confirmEmail: string) {
  return request<ApiResponse<{ deleted: boolean; email_blocked: boolean }>>(`${API_BASE}/v1/me/account`, {
    method: 'DELETE',
    body: JSON.stringify({ confirm_email: confirmEmail }),
  });
}


/* ─────────────────────── Admin API ─────────────────────── */

export async function getAdminSummary(days = 14) {
  return request<ApiResponse<AdminSummaryData>>(`${API_BASE}/v1/admin/summary?days=${days}`);
}

export async function getAdminUsers(search = '', limit = 100, offset = 0) {
  const params = new URLSearchParams({
    search,
    limit: String(limit),
    offset: String(offset),
  });
  return request<ApiResponse<AdminUsersData>>(`${API_BASE}/v1/admin/users?${params.toString()}`);
}

export async function getAdminAuditLogs(limit = 50, offset = 0) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request<ApiResponse<AdminAuditLogsData>>(`${API_BASE}/v1/admin/audit-logs?${params.toString()}`);
}

export async function getAdminUserDetail(userEmail: string) {
  return request<ApiResponse<AdminUserDetailData>>(`${API_BASE}/v1/admin/users/${encodeURIComponent(userEmail)}/detail`);
}

export async function deleteAdminUser(userEmail: string) {
  return request<ApiResponse<{ deleted: boolean; email_blocked: boolean }>>(
    `${API_BASE}/v1/admin/users/${encodeURIComponent(userEmail)}`,
    { method: 'DELETE' }
  );
}

export function getAdminTransactionsCsvUrl(): string {
  return `${API_BASE}/v1/admin/export/transactions.csv`;
}

export async function downloadAdminTransactionsCsv(): Promise<Blob> {
  const res = await fetch(getAdminTransactionsCsvUrl(), {
    headers: {
      ...authHeaders(),
    },
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const data: unknown = await res.clone().json();
      message = apiErrorMessage(data, message);
    } catch {
      const text = await res.text().catch(() => '');
      if (text) message = text;
    }
    throw new Error(message);
  }

  return res.blob();
}


export async function updateUserAdminRole(userEmail: string, isAdmin: boolean) {
  return request<ApiResponse<{ user: AdminUser }>>(
    `${API_BASE}/v1/admin/users/${encodeURIComponent(userEmail)}/admin`,
    {
      method: 'PATCH',
      body: JSON.stringify({ is_admin: isAdmin }),
    }
  );
}

export async function topUpUserTokens(userEmail: string, tokens: number, reason: string) {
  return request<ApiResponse<AdminTopUpData>>(
    `${API_BASE}/v1/admin/users/${encodeURIComponent(userEmail)}/tokens`,
    {
      method: 'POST',
      body: JSON.stringify({ tokens, reason }),
    }
  );
}


export async function getDatabaseTables() {
  return request<ApiResponse<DatabaseTablesData>>(`${API_BASE}/v1/admin/database/tables`);
}

export async function runReadOnlySql(query: string, limit = 100) {
  return request<ApiResponse<SqlQueryData>>(`${API_BASE}/v1/admin/database/query`, {
    method: 'POST',
    body: JSON.stringify({ query, limit }),
  });
}

export async function getAdminSettings() {
  return request<ApiResponse<AdminSettingsData>>(`${API_BASE}/v1/admin/settings`);
}

export async function updateAdminSetting(key: string, value: string) {
  return request<ApiResponse<{ setting: AdminSettingsData['settings'][number] }>>(
    `${API_BASE}/v1/admin/settings/${encodeURIComponent(key)}`,
    {
      method: 'PUT',
      body: JSON.stringify({ value }),
    }
  );
}

/* ─────────────────────── Payment API ─────────────────────── */

export async function createPayment(packageId: string) {
  return request<ApiResponse<PaymentCreateData>>(`${API_BASE}/v1/payment/create`, {
    method: 'POST',
    body: JSON.stringify({ package_id: packageId }),
  });
}

export async function checkPaymentStatus(paymentId: number) {
  return request<ApiResponse<PaymentStatusData>>(`${API_BASE}/v1/payment/status/${paymentId}`);
}

/**
 * Build Google OAuth login URL
 */
export function getGoogleLoginUrl(sessionId: string): string {
  return `${API_BASE}/v1/auth/google/login/flutter?session_id=${encodeURIComponent(sessionId)}`;
}
