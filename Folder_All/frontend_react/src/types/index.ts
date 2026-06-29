/* ── Chat Types ── */

export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  sources?: Source[];
  tokenUsed?: number;
  responseTime?: number;
  timestamp: number;
}

export interface Source {
  content: string;
  source: string;
  full_content?: string;
  score?: number;
  relevance_score?: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  isPinned?: boolean;
}

export interface ServerConversation {
  id: string;
  user_email: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ServerMessage {
  id: number;
  conversation_id?: string;
  user_email?: string;
  role: 'user' | 'bot';
  content: string;
  sources?: Source[];
  token_used?: number;
  response_time?: number;
  num_docs?: number;
  created_at: string;
}

/* ── Auth Types ── */

export interface User {
  email: string;
  name: string;
  picture?: string;
  is_admin?: boolean;
}

/* ── API Types ── */

export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  error_code?: string;
}

export interface ChatResponseData {
  answer: string;
  sources: Source[];
  response_time: number;
  num_docs_retrieved: number;
  num_docs_graded: number;
  token_used: number;
  conversation_id?: string;
  balance?: number;
  user_message?: ServerMessage;
  bot_message?: ServerMessage;
  conversation?: ServerConversation;
}

export interface ChatHistoryData {
  messages: Message[];
  total: number;
  user_email: string;
}

export interface ClearChatHistoryData {
  deleted: number;
  user_email: string;
}

export interface HealthData {
  status: string;
  llm_provider: string;
  vector_store: string;
  model_loaded: boolean;
}

export interface PublicContentSection {
  title: string;
  content: string;
}

export interface PublicContentData {
  privacy: PublicContentSection;
  terms: PublicContentSection;
  support: PublicContentSection & {
    email: string;
  };
}

export interface TokenTransaction {
  id: number;
  user_email: string;
  delta: number;
  reason: string;
  related_payment_id?: number | null;
  created_at: string;
}

export interface TokenBalanceData {
  user_email: string;
  token_balance: number;
  transactions: TokenTransaction[];
}

export interface ConversationListData {
  conversations: ServerConversation[];
}

export interface ConversationData {
  conversation: ServerConversation;
}

export interface ConversationMessagesData {
  messages: ServerMessage[];
}

export interface LoginSessionCreateData {
  status: string;
  session_id: string;
}

export interface LoginSessionPollData {
  status: 'pending' | 'completed';
  token?: string;
  user?: User;
}

export interface VerifyTokenData {
  valid: boolean;
  user: User;
}

/* ── Payment Types ── */

export interface PaymentCreateData {
  payment_id: number;
  hex_id: string;
  transfer_content: string;
  amount: number;
  package_id: string;
  tokens: number;
  qr_url: string;
  bank_account: string;
  bank_name: string;
  account_name: string;
  expires_at?: string | null;
  expires_in_seconds?: number;
}

export interface PaymentStatusData {
  status: 'pending' | 'completed' | 'expired';
  token_balance?: number;
  expires_at?: string | null;
}


/* ── Admin Types ── */

export interface AdminPayment {
  id: number;
  user_email: string;
  amount_vnd: number;
  package_id?: string;
  tokens: number;
  status: 'pending' | 'completed' | string;
  sepay_tx_id?: string | null;
  created_at: string;
}

export interface AdminTokenTransaction {
  id: number;
  user_email: string;
  delta: number;
  reason: string;
  related_payment_id?: number | null;
  created_at: string;
}

export interface AdminDailyMetric {
  date: string;
  revenue_vnd: number;
  payment_tokens: number;
  manual_tokens: number;
  spent_tokens: number;
  completed_payments: number;
  questions: number;
  active_users: number;
}

export interface AdminAuditLog {
  id: number;
  actor_email: string;
  action: string;
  target_type?: string;
  target_id?: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AdminAlert {
  severity: 'critical' | 'warning' | 'info' | string;
  code: string;
  message: string;
}

export interface AdminSummaryData {
  total_users: number;
  total_token_balance: number;
  total_payments: number;
  completed_payments: number;
  pending_payments: number;
  completed_revenue_vnd: number;
  payment_tokens: number;
  manual_tokens: number;
  spent_tokens: number;
  recent_payments: AdminPayment[];
  recent_transactions: AdminTokenTransaction[];
  daily_metrics: AdminDailyMetric[];
  recent_audit_logs: AdminAuditLog[];
  alerts?: AdminAlert[];
}

export interface AdminAuditLogsData {
  logs: AdminAuditLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminUser {
  id: number;
  email: string;
  name?: string;
  picture?: string;
  is_admin: boolean;
  created_at: string;
  last_login: string;
  token_balance: number;
  completed_revenue_vnd: number;
  conversation_count: number;
  message_count: number;
}


export interface AdminUserDetailData {
  user: AdminUser;
  transactions: AdminTokenTransaction[];
  payments: AdminPayment[];
  conversations: ServerConversation[];
}

export interface AdminUsersData {
  users: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminSetting {
  key: string;
  value: string;
  value_preview: string;
  has_value: boolean;
  is_secret: boolean;
  description: string;
  updated_at?: string;
  updated_by?: string;
}

export interface AdminSettingsData {
  settings: AdminSetting[];
}

export interface AdminTopUpData {
  user_email: string;
  token_balance: number;
  transaction: AdminTokenTransaction;
}

export interface AdminLoginData {
  token: string;
  user: User;
}

export interface DatabaseColumnInfo {
  name: string;
  type: string;
  notnull: boolean;
  primary_key: boolean;
}

export interface DatabaseTableInfo {
  name: string;
  row_count: number;
  columns: DatabaseColumnInfo[];
}

export interface DatabaseTablesData {
  tables: DatabaseTableInfo[];
}

export interface SqlQueryData {
  columns: string[];
  rows: Record<string, unknown>[];
  query: string;
}
