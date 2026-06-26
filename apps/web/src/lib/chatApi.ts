/**
 * 对话 Agent API 封装
 *
 * 统一的 fetch 封装：非 JSON 响应时提取真实错误文本，
 * 不再甩出 "Unexpected token 'I'" 这类看不懂的解析报错。
 */

const API_BASE = "/api";

/**
 * 统一请求：解析 JSON，失败时把真实错误文本抛出
 */
async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, options);
  } catch (e: any) {
    throw new Error(`网络请求失败：${e.message || "无法连接服务器"}`);
  }

  // 先拿原始文本，再决定怎么解析
  const text = await res.text();

  if (!res.ok) {
    // 尝试解析 JSON 错误信息
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      detail = parsed.detail || parsed.message || JSON.stringify(parsed);
    } catch {
      // 非 JSON（如 "Internal Server Error"），直接用原文
    }
    throw new Error(detail || `请求失败 (${res.status})`);
  }

  // 成功响应也容错：可能返回非 JSON
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`响应解析失败：${text.slice(0, 200)}`);
  }
}

// ---------- 类型 ----------

export interface SessionSummary {
  id: string;
  title: string;
}

export interface ToolInfo {
  name: string;
  description: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "tool";
  content: string;
  tool_name?: string;
  tool_calls?: { name: string; arguments: any }[];
  created_at?: string;
}

<<<<<<< HEAD
export interface SessionContent {
  id: string;
  title: string;
  content: string;
  content_type: string;
  output_format: string;
  is_saved: boolean;
  file_path?: string | null;
  createdAt: string;
  updatedAt: string;
}

=======
>>>>>>> origin/main
export interface SessionDetail {
  id: string;
  title: string;
  status: string;
  model: string;
  messages: ChatMessage[];
  tools: ToolInfo[];
<<<<<<< HEAD
  contents: SessionContent[];
=======
>>>>>>> origin/main
  createdAt: string;
  updatedAt: string;
}

// ---------- API ----------

/** 会话列表 */
export function listSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>(`${API_BASE}/chat/sessions`);
}

/** 新建会话 */
export function createSession(): Promise<SessionDetail> {
  return request<SessionDetail>(`${API_BASE}/chat/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
}

/** 获取单个会话详情 */
export function getSession(id: string): Promise<SessionDetail> {
  return request<SessionDetail>(`${API_BASE}/chat/sessions/${id}`);
}

/** 删除会话 */
export function deleteSession(id: string): Promise<void> {
  return request<void>(`${API_BASE}/chat/sessions/${id}`, {
    method: "DELETE",
  });
}

/** 重命名会话 */
export function renameSession(id: string, title: string): Promise<SessionDetail> {
  return request<SessionDetail>(`${API_BASE}/chat/sessions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

/** 发送消息（驱动 agent 循环） */
export function sendMessage(
  sessionId: string,
  content: string
): Promise<{ reply: string }> {
  return request<{ reply: string }>(
    `${API_BASE}/chat/sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }
  );
}
