"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUp,
  CheckCircle2,
  ChevronRight,
  Copy,
  Edit2,
  FileText,
  Image,
  Paperclip,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import {
  confirmSessionTask,
  getSession,
  sendMessageStream,
  uploadFile,
  type ChatFileMeta,
  type ChatMessage,
  type ConfirmationRequest,
  type SessionDetail,
  type TaskEvent,
  type TaskExecutionResult,
} from "@/lib/chatApi";
import Astronaut from "@/components/Astronaut";

interface ChatWindowProps {
  sessionId: string | null;
  onMessageSent?: () => void;
}

interface PendingFile extends ChatFileMeta {
  file_path: string;
}

type Turn = {
  user: ChatMessage;
  thinking: ChatMessage[];
  reply: ChatMessage | null;
};

const TASK_STATUS_META: Record<string, { label: string; tone: string }> = {
  created: { label: "已创建", tone: "bg-slate-100 text-slate-700" },
  analyzing: { label: "分析中", tone: "bg-sky-100 text-sky-700" },
  planned: { label: "已规划", tone: "bg-indigo-100 text-indigo-700" },
  awaiting_confirm: { label: "等待确认", tone: "bg-amber-100 text-amber-700" },
  executing: { label: "执行中", tone: "bg-violet-100 text-violet-700" },
  verifying: { label: "校验中", tone: "bg-cyan-100 text-cyan-700" },
  done: { label: "已完成", tone: "bg-emerald-100 text-emerald-700" },
  failed: { label: "失败", tone: "bg-rose-100 text-rose-700" },
  rejected: { label: "已拒绝", tone: "bg-rose-100 text-rose-700" },
};

const CONFIRM_KIND_META: Record<
  ConfirmationRequest["kind"],
  { title: string; summary: string; icon: typeof ShieldAlert; tone: string }
> = {
  plan_review: {
    title: "计划审阅",
    summary: "确认后开始执行这个文档任务。",
    icon: Sparkles,
    tone: "border-indigo-200 bg-indigo-50 text-indigo-700",
  },
  risky_action: {
    title: "高风险操作",
    summary: "这一步会改写文档内容，需要显式授权。",
    icon: ShieldAlert,
    tone: "border-rose-200 bg-rose-50 text-rose-700",
  },
  ambiguity_resolution: {
    title: "歧义消解",
    summary: "直接在下方输入框补充说明，再发送即可继续当前任务。",
    icon: AlertTriangle,
    tone: "border-amber-200 bg-amber-50 text-amber-700",
  },
};

const ACCEPTED_TYPES = [
  ".png,.jpg,.jpeg,.gif,.webp,.bmp",
  ".txt,.md,.csv,.json,.xml,.html,.htm",
  ".docx,.doc,.xlsx,.xls,.pdf,.pptx,.ppt",
].join(",");

function groupMessages(messages: ChatMessage[]): Turn[] {
  const turns: Turn[] = [];
  let current: Turn | null = null;

  for (const message of messages) {
    if (message.role === "user") {
      current = { user: message, thinking: [], reply: null };
      turns.push(current);
      continue;
    }

    if (!current) continue;

    if (message.role === "tool") {
      current.thinking.push(message);
      continue;
    }

    if (message.role === "assistant") {
      if (message.tool_calls && message.tool_calls.length > 0) {
        current.thinking.push(message);
      } else {
        current.reply = message;
      }
    }
  }

  return turns;
}

function getActiveAmbiguityTask(messages: ChatMessage[]): TaskEvent | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const taskEvent = messages[index].metadata?.task_event;
    if (
      taskEvent?.status === "awaiting_confirm" &&
      taskEvent.confirmation_request?.kind === "ambiguity_resolution"
    ) {
      return taskEvent;
    }
  }
  return null;
}

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}秒`;
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}分${sec}秒`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function buildAssistantCopyText(content: string, durationMs?: number, extra?: string): string {
  const parts = [content.trim()];
  if (extra?.trim()) {
    parts.push(extra.trim());
  }
  if (durationMs != null) {
    parts.push(`耗时：${formatDuration(durationMs)}`);
  }
  return parts.filter(Boolean).join("\n\n");
}

export default function ChatWindow({ sessionId, onMessageSent }: ChatWindowProps) {
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingTools, setStreamingTools] = useState<string[]>([]);
  const [thinkingElapsed, setThinkingElapsed] = useState(0);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const thinkingStartRef = useRef<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeAmbiguityTask = getActiveAmbiguityTask(session?.messages ?? []);

  const startThinkingTimer = () => {
    thinkingStartRef.current = Date.now();
    setThinkingElapsed(0);
    timerRef.current = setInterval(() => {
      if (thinkingStartRef.current) {
        setThinkingElapsed(Date.now() - thinkingStartRef.current);
      }
    }, 200);
  };

  const stopThinkingTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (thinkingStartRef.current) {
      setThinkingElapsed(Date.now() - thinkingStartRef.current);
      thinkingStartRef.current = null;
    }
  };

  const refresh = () => {
    if (!sessionId) {
      setSession(null);
      return;
    }
    getSession(sessionId).then(setSession).catch(() => setSession(null));
  };

  useEffect(() => {
    refresh();
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages, sending, streamingContent]);

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 200)}px`;
  }, [input]);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const result = await uploadFile(file);
        setPendingFiles((prev) => [
          ...prev,
          {
            id: result.id,
            filename: result.filename,
            file_type: result.file_type,
            extension: result.extension,
            file_path: result.file_path,
            size_bytes: result.size_bytes,
          },
        ]);
      }
    } catch (error: any) {
      alert(error.message || "文件上传失败");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const removePendingFile = (id: string) => {
    setPendingFiles((prev) => prev.filter((file) => file.id !== id));
  };

  const handleSend = async () => {
    const text = input.trim();
    if ((!text && pendingFiles.length === 0) || !sessionId || sending) return;

    const fileIds = pendingFiles.map((file) => file.id);
    const fileInfos = pendingFiles.map((file) => ({
      id: file.id,
      filename: file.filename,
      file_type: file.file_type,
      extension: file.extension,
      size_bytes: file.size_bytes,
    }));

    setInput("");
    setPendingFiles([]);
    setSending(true);
    setStreamingContent("");
    setStreamingTools([]);
    startThinkingTimer();

    const optimistic: ChatMessage = {
      role: "user",
      content: text,
      metadata: pendingFiles.length > 0 ? { files: fileInfos } : undefined,
      created_at: new Date().toISOString(),
    };
    setSession((prev) =>
      prev ? { ...prev, messages: [...prev.messages, optimistic], status: "thinking" } : prev
    );

    try {
      let accumulated = "";
      const fallbackPrompt =
        pendingFiles.length > 0 ? "请查看我上传的文件" : text;

      for await (const event of sendMessageStream(sessionId, text || fallbackPrompt, fileIds)) {
        if (event.type === "text") {
          accumulated += event.content;
          setStreamingContent(accumulated);
        } else if (event.type === "tool_call") {
          setStreamingTools(event.tools);
        } else if (event.type === "done") {
          stopThinkingTimer();
          refresh();
          onMessageSent?.();
        } else if (event.type === "error") {
          stopThinkingTimer();
          throw new Error(event.message);
        }
      }
    } catch (error: any) {
      stopThinkingTimer();
      setSession((prev) => (prev ? { ...prev, status: "error" } : prev));
      alert(error.message || "发送失败");
      refresh();
    } finally {
      stopThinkingTimer();
      setSending(false);
      setStreamingContent("");
      setStreamingTools([]);
    }
  };

  const handleTaskDecision = async (taskId: string, confirmed: boolean) => {
    if (!sessionId || sending) return;

    setSending(true);
    setStreamingTools([]);
    setStreamingContent(confirmed ? "正在继续处理文档任务..." : "正在停止当前文档任务...");
    startThinkingTimer();

    try {
      await confirmSessionTask(sessionId, taskId, confirmed);
      refresh();
      onMessageSent?.();
    } catch (error: any) {
      alert(error.message || "任务处理失败");
      refresh();
    } finally {
      stopThinkingTimer();
      setSending(false);
      setStreamingContent("");
      setStreamingTools([]);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      handleSend();
    }
  };

  const turns = session ? groupMessages(session.messages) : [];

  const handleEditMessage = (content: string) => {
    setInput(content);
    textareaRef.current?.focus();
  };

  function handleSendQuick(text: string) {
    setInput(text);
    setTimeout(() => handleSend(), 50);
  }

  return (
    <div className="flex flex-1 flex-col bg-white">
      <div className="flex-1 overflow-y-auto">
        {!session ? (
          <EmptyState />
        ) : turns.length === 0 && !sending ? (
          <WelcomeScreen onSend={handleSendQuick} />
        ) : (
          <div className="mx-auto w-full max-w-3xl px-8 pb-4 pt-2">
            {turns.map((turn, index) => (
              <TurnView
                key={`turn-${index}-${turn.user.created_at ?? index}`}
                turn={turn}
                onEdit={handleEditMessage}
                onTaskDecision={handleTaskDecision}
              />
            ))}
            {sending && (
              <div>
                {streamingTools.length > 0 && (
                  <div className="mb-2 ml-11">
                    <div className="flex items-center gap-1.5 text-xs text-gray-400">
                      <ChevronRight size={12} className="rotate-90" strokeWidth={2} />
                      思考过程
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-500">
                        {streamingTools.length} 次工具调用
                      </span>
                    </div>
                    <div className="mt-1 space-y-0.5">
                      {streamingTools.map((name, index) => (
                        <div
                          key={`${name}-${index}`}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-gray-50 px-2.5 py-1.5 text-xs text-gray-500 ring-1 ring-gray-200/60"
                        >
                          <FileText size={11} className="text-gray-400" strokeWidth={2} />
                          <span className="font-medium text-gray-600">{name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="flex items-start gap-3 py-3">
                  <div className="mt-0.5 flex-shrink-0">
                    <Astronaut size={32} animated={true} />
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col items-start gap-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-gray-500">DocFlow</span>
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-mono text-[10px] text-emerald-600">
                        {formatDuration(thinkingElapsed)}
                      </span>
                    </div>
                    <div className="max-w-full whitespace-pre-wrap rounded-2xl rounded-tl-sm bg-emerald-50 px-4 py-3 text-[14px] leading-relaxed text-gray-800">
                      {streamingContent || (
                        <span className="flex items-center gap-1.5 text-gray-400">
                          <span className="think-dot h-1.5 w-1.5 rounded-full bg-gray-300" />
                          <span className="think-dot h-1.5 w-1.5 rounded-full bg-gray-300" />
                          <span className="think-dot h-1.5 w-1.5 rounded-full bg-gray-300" />
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="px-4 pb-4 pt-2">
        <div className="mx-auto w-full max-w-3xl">
          {pendingFiles.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {pendingFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs"
                >
                  {file.file_type === "image" ? (
                    <Image size={13} className="text-blue-500" strokeWidth={2} />
                  ) : (
                    <FileText size={13} className="text-gray-500" strokeWidth={2} />
                  )}
                  <span className="max-w-[120px] truncate text-gray-700">{file.filename}</span>
                  <span className="text-gray-400">{formatFileSize(file.size_bytes)}</span>
                  {!sending && (
                    <button
                      onClick={() => removePendingFile(file.id)}
                      className="ml-1 text-gray-400 hover:text-red-500"
                    >
                      <X size={12} strokeWidth={2} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2 rounded-3xl border border-gray-200 bg-white px-4 py-3 shadow-sm transition focus-within:border-gray-300 focus-within:shadow-md">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ACCEPTED_TYPES}
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={sending || uploading}
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-40"
              title="上传文件"
            >
              {uploading ? (
                <span className="think-dot h-3 w-3 rounded-full bg-gray-300" />
              ) : (
                <Paperclip size={16} strokeWidth={2} />
              )}
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!sessionId || sending}
              placeholder={
                sessionId
                  ? activeAmbiguityTask
                    ? "补充文档要求，按 Enter 继续当前任务"
                    : pendingFiles.length > 0
                      ? "直接描述你的处理需求，按 Enter 发送"
                      : "给 DocFlow 发送消息"
                  : "请先选择或新建会话"
              }
              rows={1}
              className="max-h-[200px] flex-1 resize-none bg-transparent py-1 text-[15px] text-gray-800 outline-none placeholder:text-gray-400 disabled:cursor-not-allowed"
            />
            <button
              onClick={handleSend}
              disabled={!sessionId || sending || (!input.trim() && pendingFiles.length === 0)}
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-800 text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400"
            >
              <ArrowUp size={16} strokeWidth={2.5} />
            </button>
          </div>
          <p className="mt-2 text-center text-[11px] text-gray-400">
            DocFlow 可能会出错，请核实重要信息。
          </p>
        </div>
      </div>
    </div>
  );
}

function TurnView({
  turn,
  onEdit,
  onTaskDecision,
}: {
  turn: Turn;
  onEdit?: (content: string) => void;
  onTaskDecision: (taskId: string, confirmed: boolean) => void;
}) {
  const [showThinking, setShowThinking] = useState(false);
  const [copied, setCopied] = useState<"user" | "assistant" | null>(null);
  const hasThinking = turn.thinking.length > 0;
  const taskEvent = turn.reply?.metadata?.task_event;
  const responseMs = turn.reply?.metadata?.response_ms;

  const handleCopy = () => {
    navigator.clipboard.writeText(turn.user.content);
    setCopied("user");
    setTimeout(() => setCopied(null), 2000);
  };

  const handleCopyAssistant = () => {
    if (!turn.reply) return;

    const extra =
      taskEvent?.plan_display || taskEvent?.message || taskEvent?.error || undefined;
    navigator.clipboard.writeText(
      buildAssistantCopyText(turn.reply.content, responseMs, extra)
    );
    setCopied("assistant");
    setTimeout(() => setCopied(null), 2000);
  };

  const handleEdit = () => {
    if (onEdit) onEdit(turn.user.content);
  };

  return (
    <div className="animate-fade-in">
      <UserBubble
        content={turn.user.content}
        files={turn.user.metadata?.files}
        onCopy={turn.user.content ? handleCopy : undefined}
        onEdit={turn.user.content ? handleEdit : undefined}
      />
      {copied && (
        <div className="fixed right-4 top-4 z-50 rounded-lg bg-gray-800 px-4 py-2 text-sm text-white shadow-lg">
          {copied === "assistant" ? "已复制 AI 回答" : "已复制到剪贴板"}
        </div>
      )}

      {hasThinking && (
        <div className="mb-2 ml-11">
          <button
            onClick={() => setShowThinking((value) => !value)}
            className="flex items-center gap-1.5 text-xs text-gray-400 transition hover:text-gray-600"
          >
            <ChevronRight
              size={12}
              className={`transition-transform ${showThinking ? "rotate-90" : ""}`}
              strokeWidth={2}
            />
            思考过程
            <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-500">
              {turn.thinking.filter((message) => message.role === "assistant").length} 次工具调用
            </span>
          </button>
          {showThinking && (
            <div className="mt-1 space-y-1">
              {turn.thinking.map((message, index) => {
                if (message.role === "assistant" && message.tool_calls) {
                  return (
                    <div key={index} className="space-y-0.5">
                      {message.tool_calls.map((toolCall, toolIndex) => (
                        <div
                          key={`${toolCall.name}-${toolIndex}`}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-gray-50 px-2.5 py-1.5 text-xs text-gray-500 ring-1 ring-gray-200/60"
                        >
                          <FileText size={11} className="text-gray-400" strokeWidth={2} />
                          <span className="font-medium text-gray-600">{toolCall.name}</span>
                        </div>
                      ))}
                    </div>
                  );
                }
                if (message.role === "tool") {
                  return (
                    <pre
                      key={index}
                      className="max-h-40 overflow-auto rounded-lg bg-gray-50 p-3 font-mono text-xs leading-relaxed text-gray-500 ring-1 ring-gray-100"
                    >
                      {message.content}
                    </pre>
                  );
                }
                return null;
              })}
            </div>
          )}
        </div>
      )}

      {turn.reply &&
        (taskEvent ? (
          <TaskAssistantBubble
            content={turn.reply.content}
            task={taskEvent}
            durationMs={responseMs}
            onConfirm={() => onTaskDecision(taskEvent.task_id, true)}
            onReject={() => onTaskDecision(taskEvent.task_id, false)}
            onCopy={handleCopyAssistant}
          />
        ) : (
          <AssistantBubble
            content={turn.reply.content}
            durationMs={responseMs}
            onCopy={handleCopyAssistant}
          />
        ))}
    </div>
  );
}

function UserBubble({
  content,
  files,
  onCopy,
  onEdit,
}: {
  content: string;
  files?: ChatFileMeta[];
  onCopy?: () => void;
  onEdit?: () => void;
}) {
  return (
    <div className="group flex items-start justify-end gap-3 py-3">
      <div className="relative max-w-[78%]">
        {files && files.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs"
              >
                {file.file_type === "image" ? (
                  <Image size={13} className="text-blue-500" strokeWidth={2} />
                ) : (
                  <FileText size={13} className="text-gray-500" strokeWidth={2} />
                )}
                <span className="max-w-[120px] truncate text-gray-700">{file.filename}</span>
                <span className="text-gray-400">{formatFileSize(file.size_bytes)}</span>
              </div>
            ))}
          </div>
        )}
        {content && (
          <div className="rounded-2xl rounded-tr-sm bg-gray-100 px-4 py-3 text-[14px] leading-relaxed text-gray-900">
            {content}
          </div>
        )}
        <div className="mt-1 flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          {onCopy && (
            <button
              onClick={onCopy}
              className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
              title="复制"
            >
              <Copy size={14} />
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
              title="编辑"
            >
              <Edit2 size={14} />
            </button>
          )}
        </div>
      </div>
      <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-800 text-white">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </div>
    </div>
  );
}

function AssistantBubble({
  content,
  durationMs,
  onCopy,
}: {
  content: string;
  durationMs?: number;
  onCopy?: () => void;
}) {
  return (
    <div className="group flex items-start gap-3 py-3">
      <div className="mt-0.5 flex-shrink-0">
        <Astronaut size={32} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-gray-500">DocFlow</span>
          {durationMs != null && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-mono text-[10px] text-emerald-600">
              {formatDuration(durationMs)}
            </span>
          )}
        </div>
        <div className="max-w-full whitespace-pre-wrap rounded-2xl rounded-tl-sm bg-emerald-50 px-4 py-3 text-[14px] leading-relaxed text-gray-800">
          {content || "（无内容）"}
        </div>
        {onCopy && (
          <button
            onClick={onCopy}
            className="rounded p-1 text-gray-400 opacity-0 transition hover:bg-gray-100 hover:text-gray-600 group-hover:opacity-100"
            title="复制回答"
          >
            <Copy size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

function TaskAssistantBubble({
  content,
  task,
  durationMs,
  onConfirm,
  onReject,
  onCopy,
}: {
  content: string;
  task: TaskEvent;
  durationMs?: number;
  onConfirm: () => void;
  onReject: () => void;
  onCopy?: () => void;
}) {
  const statusMeta = TASK_STATUS_META[task.status] ?? TASK_STATUS_META.created;
  const confirmMeta = task.confirmation_request
    ? CONFIRM_KIND_META[task.confirmation_request.kind]
    : null;
  const ConfirmIcon = confirmMeta?.icon;

  return (
    <div className="group flex items-start gap-3 py-3">
      <div className="mt-0.5 flex-shrink-0">
        <Astronaut size={32} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-gray-500">DocFlow</span>
          {durationMs != null && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-mono text-[10px] text-emerald-600">
              {formatDuration(durationMs)}
            </span>
          )}
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${statusMeta.tone}`}>
            {statusMeta.label}
          </span>
        </div>

        <div className="w-full rounded-2xl rounded-tl-sm bg-emerald-50 px-4 py-3 text-[14px] leading-relaxed text-gray-800">
          <p className="font-medium text-gray-900">{content}</p>
          {task.plan_display && (
            <pre className="mt-2 whitespace-pre-wrap break-words text-[12px] leading-relaxed text-gray-700">
              {task.plan_display}
            </pre>
          )}
        </div>

        {confirmMeta && ConfirmIcon ? (
          <div className={`w-full rounded-2xl border px-4 py-3 ${confirmMeta.tone}`}>
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-white/70 p-2">
                <ConfirmIcon size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[13px] font-semibold">{confirmMeta.title}</p>
                  <span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] uppercase">
                    {task.confirmation_request?.stage}
                  </span>
                </div>
                <p className="mt-1 text-[12px] leading-relaxed">
                  {task.confirmation_request?.message}
                </p>
                <p className="mt-2 text-[11px] opacity-80">{confirmMeta.summary}</p>
                {Object.keys(task.confirmation_request?.details ?? {}).length > 0 && (
                  <pre className="mt-3 whitespace-pre-wrap break-words rounded-xl bg-white/60 p-3 text-[11px] text-current">
                    {JSON.stringify(task.confirmation_request?.details ?? {}, null, 2)}
                  </pre>
                )}
                {task.confirmation_request?.kind !== "ambiguity_resolution" && (
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={onConfirm}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-white px-3 py-2 text-[12px] font-medium text-gray-900 ring-1 ring-black/10 transition hover:bg-gray-50"
                    >
                      <CheckCircle2 size={13} />
                      确认执行
                    </button>
                    <button
                      onClick={onReject}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-white/70 px-3 py-2 text-[12px] font-medium ring-1 ring-black/10 transition hover:bg-white"
                    >
                      <X size={13} />
                      拒绝
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : null}

        {task.message && (
          <div className="w-full rounded-xl bg-gray-100 px-3 py-2 text-[12px] text-gray-600">
            {task.message}
          </div>
        )}

        {task.error && (
          <div className="w-full rounded-xl bg-rose-50 px-3 py-2 text-[12px] text-rose-700">
            {task.error}
          </div>
        )}

        {task.result && <TaskResultPanel result={task.result} />}

        {onCopy && (
          <button
            onClick={onCopy}
            className="rounded p-1 text-gray-400 opacity-0 transition hover:bg-gray-100 hover:text-gray-600 group-hover:opacity-100"
            title="复制回答"
          >
            <Copy size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

function TaskResultPanel({ result }: { result: TaskExecutionResult }) {
  return (
    <div className="w-full rounded-xl border border-gray-200 bg-white px-3 py-3">
      <div className="flex items-center gap-2 text-[12px] font-medium">
        {result.success ? (
          <>
            <CheckCircle2 size={14} className="text-emerald-600" />
            <span className="text-emerald-700">执行与校验通过</span>
          </>
        ) : (
          <>
            <AlertTriangle size={14} className="text-amber-600" />
            <span className="text-amber-700">执行失败或仍需处理</span>
          </>
        )}
      </div>
      {result.error && (
        <p className="mt-2 text-[12px] leading-relaxed text-rose-700">{result.error}</p>
      )}
      {result.verification?.checks && result.verification.checks.length > 0 && (
        <div className="mt-3 space-y-2">
          {result.verification.checks.map((check, index) => (
            <div key={`${check.name}-${index}`} className="rounded-lg bg-gray-50 px-3 py-2 text-[11px]">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-1.5 py-0.5 ${
                    check.passed ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                  }`}
                >
                  {check.passed ? "通过" : "未通过"}
                </span>
                <span className="font-medium text-gray-700">{check.name}</span>
              </div>
              <p className="mt-1 text-gray-500">{check.detail}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WelcomeScreen({ onSend }: { onSend: (text: string) => void }) {
  const suggestions = [
    { icon: "📝", text: "帮我写一篇会议纪要", sub: "整理会议要点" },
    { icon: "✍️", text: "帮我润色一段文字", sub: "让表达更流畅" },
    { icon: "📋", text: "列一份工作计划", sub: "按优先级排序" },
    { icon: "💡", text: "给我一些创意灵感", sub: "激发写作思路" },
  ];

  return (
    <div className="flex h-full flex-col items-center justify-center px-8">
      <Astronaut size={64} />
      <h1 className="mt-5 text-2xl font-semibold text-gray-800">有什么可以帮你的？</h1>
      <div className="mt-8 grid w-full max-w-2xl grid-cols-2 gap-3">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSend(suggestion.text)}
            className="flex items-start gap-3 rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:bg-gray-50"
          >
            <span className="mt-0.5 text-xl">{suggestion.icon}</span>
            <div>
              <p className="text-[13px] font-medium text-gray-800">{suggestion.text}</p>
              <p className="mt-0.5 text-[12px] text-gray-400">{suggestion.sub}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <Astronaut size={64} />
      <p className="mt-4 text-base font-semibold text-gray-700">DocFlow 办公助手</p>
      <p className="mt-1 text-sm text-gray-400">从左侧选择一个会话，或开始新对话</p>
    </div>
  );
}
