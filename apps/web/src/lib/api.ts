/**
 * API 调用封装
 */

const API_BASE = "/api";

export interface TaskResponse {
  task_id: string;
  status: string;
  plan_display: string;
  needs_confirmation: boolean;
  confirmation_request: ConfirmationRequest | null;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  task_type: string;
  error: string | null;
  confirmation_request: ConfirmationRequest | null;
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

export interface UploadResponse {
  id: string;
  filename: string;
  file_type: string;
  extension: string;
  file_path: string;
  size_bytes: number;
  extracted_text?: string;
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

export interface ConfirmTaskResponse {
  status: string;
  message?: string;
  confirmation_request?: ConfirmationRequest | null;
  plan_display?: string;
  needs_confirmation?: boolean;
  result?: TaskExecutionResult;
}

/**
 * 上传文件
 */
export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/files/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json();
    const detail = error.detail || "Upload failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return res.json();
}

/**
 * 创建任务并生成计划
 */
export async function createTask(
  filePath: string,
  userInput: string
): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE}/tasks/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_path: filePath,
      user_input: userInput,
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Create task failed");
  }

  return res.json();
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Get task failed");
  }

  return res.json();
}

/**
 * 确认任务
 */
export async function confirmTask(
  taskId: string,
  confirmed: boolean,
  userInput?: string
): Promise<ConfirmTaskResponse> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_id: taskId,
      confirmed: confirmed,
      user_input: userInput,
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Confirm task failed");
  }

  return res.json();
}

/**
 * 下载文件
 */
export function downloadFile(fileId: string) {
  window.open(`${API_BASE}/files/download/${fileId}`, "_blank");
}
