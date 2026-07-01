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

  const text = await res.text();

  if (!res.ok) {
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      detail = parsed.detail || parsed.message || JSON.stringify(parsed);
    } catch {
    }
    throw new Error(detail || `请求失败 (${res.status})`);
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`响应解析失败：${text.slice(0, 200)}`);
  }
}

export interface SessionSummary {
  id: string;
  title: string;
}

export interface ChatFileMeta {
  id: string;
  filename: string;
  file_type: string;
  extension: string;
  size_bytes: number;
}

export interface ConfirmationRequest {
  request_id: string;
  kind: "plan_review" | "risky_action" | "ambiguity_resolution";
  stage: "analyzing" | "planned" | "executing";
  message: string;
  blocking: boolean;
  options: string[];
  details: Record<string, unknown>;
  resume_from: string | null;
}

export interface VerificationCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface ExecutionActionResult {
  action_id: string;
  tool_name: string;
  success: boolean;
  output: Record<string, unknown>;
  error: string | null;
}

export interface TaskExecutionResult {
  success: boolean;
  error?: string;
  verification?: {
    passed: boolean;
    checks: VerificationCheck[];
  };
  execution_results?: ExecutionActionResult[];
}

export interface TaskEvent {
  task_id: string;
  status: string;
  plan_display?: string;
  confirmation_request?: ConfirmationRequest | null;
  result?: TaskExecutionResult | null;
  message?: string | null;
  error?: string | null;
}

export interface ChatMessageMetadata {
  files?: ChatFileMeta[];
  task_event?: TaskEvent;
  response_ms?: number;
}

export interface ChatMessage {
  role: "user" | "assistant" | "tool";
  content: string;
  tool_name?: string;
  tool_calls?: { name: string; arguments: any }[];
  created_at?: string;
  metadata?: ChatMessageMetadata;
}

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

export interface SessionDetail {
  id: string;
  title: string;
  status: string;
  model: string;
  messages: ChatMessage[];
  contents: SessionContent[];
  createdAt: string;
  updatedAt: string;
}

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
  content: string,
  fileIds: string[] = []
): Promise<{ reply: string; message?: ChatMessage }> {
  return request<{ reply: string; message?: ChatMessage }>(
    `${API_BASE}/chat/sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, file_ids: fileIds }),
    }
  );
}

/** 上传文件 */
export async function uploadFile(file: File): Promise<{
  id: string;
  filename: string;
  file_type: string;
  extension: string;
  file_path: string;
  size_bytes: number;
  extracted_text?: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/files/upload`, {
      method: "POST",
      body: formData,
    });
  } catch (e: any) {
    throw new Error(`网络请求失败：${e.message || "无法连接服务器"}`);
  }

  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      const raw = parsed.detail || parsed.message || parsed;
      // 确保 detail 是字符串，避免 [object Object]
      detail = typeof raw === "string" ? raw : JSON.stringify(raw);
    } catch {}
    throw new Error(detail || `请求失败 (${res.status})`);
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`响应解析失败：${text.slice(0, 200)}`);
  }
}

/** 流式事件类型 */
export type StreamEvent =
  | { type: "text"; content: string }
  | { type: "tool_call"; tools: string[] }
  | { type: "tool_result"; name: string; result: any }
  | { type: "done" }
  | { type: "error"; message: string };

/** 流式发送消息，返回异步迭代器 */
export async function* sendMessageStream(
  sessionId: string,
  content: string,
  fileIds: string[] = []
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, file_ids: fileIds }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `请求失败 (${res.status})`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("无法读取响应流");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    
    // 按 SSE 格式分割（每个事件以 \n\n 结束）
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      const lines = event.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data.trim()) {
            try {
              const parsed = JSON.parse(data) as StreamEvent;
              yield parsed;
            } catch (e) {
              console.warn("SSE 解析失败:", data, e);
            }
          }
        }
      }
    }
  }
}

export function confirmSessionTask(
  sessionId: string,
  taskId: string,
  confirmed: boolean,
  userInput?: string
): Promise<{ message: ChatMessage; session: SessionDetail }> {
  return request<{ message: ChatMessage; session: SessionDetail }>(
    `${API_BASE}/chat/sessions/${sessionId}/tasks/${taskId}/confirm`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirmed,
        user_input: userInput,
      }),
    }
  );
}
