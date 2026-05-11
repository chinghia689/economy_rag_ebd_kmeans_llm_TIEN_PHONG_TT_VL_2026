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
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
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
}

export interface PaymentStatusData {
  status: 'pending' | 'completed';
  token_balance?: number;
}
