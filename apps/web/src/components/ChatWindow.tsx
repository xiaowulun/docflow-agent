"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, ChevronRight, Paperclip, X, FileText, Image, Copy, Edit2 } from "lucide-react";
import {
  getSession,
  sendMessageStream,
  uploadFile,
  type SessionDetail,
  type ChatMessage,
} from "@/lib/chatApi";
import Astronaut from "@/components/Astronaut";

interface ChatWindowProps {
  sessionId: string | null;
  onMessageSent?: () => void;
}

/** 待发送的文件 */
interface PendingFile {
  id: string;
  filename: string;
  file_type: string;
  extension: string;
  size_bytes: number;
}

/**
 * 按"轮次"分组消息：每条用户消息 + 后续所有 assistant/tool 消息为一组
 */
type Turn = {
  user: ChatMessage;
  thinking: ChatMessage[];
  reply: ChatMessage | null;
};

function groupMessages(messages: ChatMessage[]): Turn[] {
  const turns: Turn[] = [];
  let current: Turn | null = null;

  for (const m of messages) {
    if (m.role === "user") {
      current = { user: m, thinking: [], reply: null };
      turns.push(current);
    } else if (current) {
      if (m.role === "tool") {
        current.thinking.push(m);
      } else if (m.role === "assistant") {
        if (m.tool_calls && m.tool_calls.length > 0) {
          current.thinking.push(m);
        } else {
          current.reply = m;
        }
      }
    }
  }

  return turns;
}

/** 格式化耗时为 "X秒" 或 "X分Y秒" */
function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}秒`;
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}分${sec}秒`;
}

/** 格式化文件大小 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

const ACCEPTED_TYPES = [
  // 图片
  ".png,.jpg,.jpeg,.gif,.webp,.bmp",
  // 文档
  ".txt,.md,.csv,.json,.xml,.html,.htm",
  ".docx,.doc,.xlsx,.xls,.pdf,.pptx,.ppt",
].join(",");

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
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [input]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
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
            size_bytes: result.size_bytes,
          },
        ]);
      }
    } catch (e: any) {
      alert(e.message || "文件上传失败");
    } finally {
      setUploading(false);
      // 清空 input 以允许重复选择同一文件
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const removePendingFile = (id: string) => {
    setPendingFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSend = async () => {
    const text = input.trim();
    if ((!text && pendingFiles.length === 0) || !sessionId || sending) return;

    const fileIds = pendingFiles.map((f) => f.id);
    const fileInfos = pendingFiles.map((f) => ({
      id: f.id, filename: f.filename, file_type: f.file_type,
      extension: f.extension, size_bytes: f.size_bytes,
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
      prev
        ? { ...prev, messages: [...prev.messages, optimistic], status: "thinking" }
        : prev
    );

    try {
      let accumulated = "";
      for await (const event of sendMessageStream(sessionId, text || "请查看我上传的文件", fileIds)) {
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
    } catch (e: any) {
      stopThinkingTimer();
      setSession((prev) => (prev ? { ...prev, status: "error" } : prev));
      alert(e.message || "发送失败");
      refresh();
    } finally {
      stopThinkingTimer();
      setSending(false);
      setStreamingContent("");
      setStreamingTools([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const turns = session ? groupMessages(session.messages) : [];

  const handleEditMessage = (content: string) => {
    setInput(content);
    textareaRef.current?.focus();
  };

  return (
    <div className="flex flex-1 flex-col bg-white">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {!session ? (
          <EmptyState />
        ) : turns.length === 0 && !sending ? (
          <WelcomeScreen onSend={handleSendQuick} />
        ) : (
          <div className="mx-auto w-full max-w-3xl px-8 pb-4 pt-2">
            {turns.map((turn, ti) => (
              <TurnView key={ti} turn={turn} onEdit={handleEditMessage} />
            ))}
            {sending && (
              <div>
                {streamingTools.length > 0 && (
                  <div className="ml-11 mb-2">
                    <div className="flex items-center gap-1.5 text-xs text-gray-400">
                      <ChevronRight size={12} className="rotate-90" strokeWidth={2} />
                      思考过程
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-500">
                        {streamingTools.length} 次工具调用
                      </span>
                    </div>
                    <div className="mt-1 space-y-0.5">
                      {streamingTools.map((name, i) => (
                        <div
                          key={i}
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

      {/* Input */}
      <div className="px-4 pb-4 pt-2">
        <div className="mx-auto w-full max-w-3xl">
          {/* 待发送文件预览 */}
          {pendingFiles.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {pendingFiles.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs"
                >
                  {f.file_type === "image" ? (
                    <Image size={13} className="text-blue-500" strokeWidth={2} />
                  ) : (
                    <FileText size={13} className="text-gray-500" strokeWidth={2} />
                  )}
                  <span className="max-w-[120px] truncate text-gray-700">{f.filename}</span>
                  <span className="text-gray-400">{formatFileSize(f.size_bytes)}</span>
                  {!sending && (
                    <button
                      onClick={() => removePendingFile(f.id)}
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
            {/* 上传按钮 */}
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
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!sessionId || sending}
              placeholder={
                sessionId
                  ? pendingFiles.length > 0
                    ? "添加说明（可选），按 Enter 发送"
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

  function handleSendQuick(text: string) {
    setInput(text);
    setTimeout(() => handleSend(), 50);
  }
}

/** 渲染一轮对话 */
function TurnView({ turn, onEdit }: { turn: Turn; onEdit?: (content: string) => void }) {
  const [showThinking, setShowThinking] = useState(false);
  const [copied, setCopied] = useState(false);
  const hasThinking = turn.thinking.length > 0;

  const handleCopy = () => {
    navigator.clipboard.writeText(turn.user.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEdit = () => {
    if (onEdit) {
      onEdit(turn.user.content);
    }
  };

  return (
    <div className="animate-fade-in">
      <UserBubble 
        content={turn.user.content} 
        files={turn.user.metadata?.files}
        onCopy={handleCopy}
        onEdit={handleEdit}
      />
      {copied && (
        <div className="fixed top-4 right-4 z-50 rounded-lg bg-gray-800 px-4 py-2 text-sm text-white shadow-lg">
          已复制到剪贴板
        </div>
      )}

      {hasThinking && (
        <div className="ml-11 mb-2">
          <button
            onClick={() => setShowThinking((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-gray-400 transition hover:text-gray-600"
          >
            <ChevronRight
              size={12}
              className={`transition-transform ${showThinking ? "rotate-90" : ""}`}
              strokeWidth={2}
            />
            思考过程
            <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-500">
              {turn.thinking.filter((m) => m.role === "assistant").length} 次工具调用
            </span>
          </button>
          {showThinking && (
            <div className="mt-1 space-y-1">
              {turn.thinking.map((m, i) => {
                if (m.role === "assistant" && m.tool_calls) {
                  return (
                    <div key={i} className="space-y-0.5">
                      {m.tool_calls.map((tc, j) => (
                        <div
                          key={j}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-gray-50 px-2.5 py-1.5 text-xs text-gray-500 ring-1 ring-gray-200/60"
                        >
                          <FileText size={11} className="text-gray-400" strokeWidth={2} />
                          <span className="font-medium text-gray-600">{tc.name}</span>
                        </div>
                      ))}
                    </div>
                  );
                }
                if (m.role === "tool") {
                  return (
                    <pre
                      key={i}
                      className="max-h-40 overflow-auto rounded-lg bg-gray-50 p-3 font-mono text-xs leading-relaxed text-gray-500 ring-1 ring-gray-100"
                    >
                      {m.content}
                    </pre>
                  );
                }
                return null;
              })}
            </div>
          )}
        </div>
      )}

      {turn.reply && <AssistantBubble content={turn.reply.content} />}
    </div>
  );
}

function UserBubble({ content, files, onCopy, onEdit }: { 
  content: string; 
  files?: Array<{id: string; filename: string; file_type: string; extension: string; size_bytes: number}>;
  onCopy?: () => void; 
  onEdit?: () => void 
}) {
  return (
    <div className="group flex items-start justify-end gap-3 py-3">
      <div className="relative max-w-[78%]">
        {/* 文件附件卡片 */}
        {files && files.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {files.map((f) => (
              <div
                key={f.id}
                className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs"
              >
                {f.file_type === "image" ? (
                  <Image size={13} className="text-blue-500" strokeWidth={2} />
                ) : (
                  <FileText size={13} className="text-gray-500" strokeWidth={2} />
                )}
                <span className="max-w-[120px] truncate text-gray-700">{f.filename}</span>
                <span className="text-gray-400">{formatFileSize(f.size_bytes)}</span>
              </div>
            ))}
          </div>
        )}
        {/* 用户文字内容 */}
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

function AssistantBubble({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <div className="mt-0.5 flex-shrink-0">
        <Astronaut size={32} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1.5">
        <span className="text-[11px] font-semibold text-gray-500">DocFlow</span>
        <div className="max-w-full whitespace-pre-wrap rounded-2xl rounded-tl-sm bg-emerald-50 px-4 py-3 text-[14px] leading-relaxed text-gray-800">
          {content || "（无内容）"}
        </div>
      </div>
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
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSend(s.text)}
            className="flex items-start gap-3 rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:bg-gray-50"
          >
            <span className="mt-0.5 text-xl">{s.icon}</span>
            <div>
              <p className="text-[13px] font-medium text-gray-800">{s.text}</p>
              <p className="mt-0.5 text-[12px] text-gray-400">{s.sub}</p>
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
