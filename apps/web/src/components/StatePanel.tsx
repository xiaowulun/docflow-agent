"use client";

import { useEffect, useState } from "react";
import { FileText, AlertTriangle, Activity } from "lucide-react";
import { getSession, type SessionDetail } from "@/lib/chatApi";

interface StatePanelProps {
  sessionId: string | null;
  refreshKey?: number;
}

function estimateTokens(messages: { content: string; role: string }[]): number {
  let total = 0;
  for (const m of messages) {
    const cjk = (m.content.match(/[\u4e00-\u9fff]/g) || []).length;
    const nonCjk = m.content.length - cjk;
    total += Math.ceil(cjk * 1.5 + nonCjk / 4);
  }
  total += messages.length * 4;
  return total;
}

function getContextWindow(model: string): number {
  if (model.includes("gpt-4o")) return 128000;
  if (model.includes("deepseek")) return 65536;
  if (model.includes("claude")) return 200000;
  return 65536;
}

export default function StatePanel({ sessionId, refreshKey = 0 }: StatePanelProps) {
  const [session, setSession] = useState<SessionDetail | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      return;
    }
    getSession(sessionId).then(setSession).catch(() => setSession(null));
  }, [sessionId, refreshKey]);

  const isOk = session ? session.status !== "error" : true;
  const usedTokens = estimateTokens(session?.messages ?? []);
  const maxTokens = getContextWindow(session?.model ?? "");
  const percent = Math.min((usedTokens / maxTokens) * 100, 100);
  const barColor =
    percent > 80 ? "bg-red-500" : percent > 50 ? "bg-amber-500" : "bg-emerald-500";

  return (
    <aside className="flex w-64 flex-shrink-0 flex-col border-l border-gray-200/80 bg-[#f9f9f9]">
      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
        {/* Status */}
        <div className="flex items-center gap-2">
          <span className={`inline-block h-2 w-2 rounded-full ${isOk ? "bg-emerald-500" : "bg-red-500"}`} />
          <span className={`text-[13px] font-medium ${isOk ? "text-emerald-600" : "text-red-600"}`}>
            {session ? (isOk ? "运行正常" : "出错了") : "会话未选中"}
          </span>
        </div>

        {/* Meta */}
        <div>
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-gray-400">会话信息</p>
          <div className="space-y-2 rounded-xl border border-gray-200/80 bg-white p-3">
            <Meta label="消息数" value={String(session?.messages?.length ?? 0)} />
            <Meta label="模型" value={session?.model ?? "-"} mono />
            <Meta label="创建" value={session ? formatTime(session.createdAt) : "-"} />
            <Meta label="更新" value={session ? formatTime(session.updatedAt) : "-"} />
          </div>
        </div>

        {/* Pending */}
        {session?.status === "awaiting_confirmation" && (
          <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-2.5 ring-1 ring-amber-100">
            <AlertTriangle size={13} className="mt-0.5 flex-shrink-0 text-amber-500" strokeWidth={2} />
            <p className="text-[11px] leading-relaxed text-amber-700">
              当前会话有待确认步骤，直接在中间对话区继续处理即可。
            </p>
          </div>
        )}

        {/* Documents */}
        <div>
          <div className="mb-2 flex items-center gap-1.5">
            <FileText size={12} className="text-gray-400" strokeWidth={2} />
            <span className="text-[11px] font-medium uppercase tracking-wider text-gray-400">文档列表</span>
          </div>
          {(session?.contents ?? []).length === 0 ? (
            <p className="rounded-lg border border-dashed border-gray-200 py-4 text-center text-[11px] text-gray-400">
              {session ? "暂无文档" : "先选择一个聊天会话"}
            </p>
          ) : (
            <div className="space-y-2">
              {(session?.contents ?? []).map((item) => (
                <div key={item.id} className="rounded-lg border border-gray-200/80 bg-white p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-[12px] font-medium text-gray-800">{item.title}</span>
                    <span
                      className={`flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        item.is_saved
                          ? "bg-emerald-50 text-emerald-600"
                          : "bg-amber-50 text-amber-600"
                      }`}
                    >
                      {item.is_saved ? item.output_format : "草稿"}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 whitespace-pre-wrap text-[11px] leading-relaxed text-gray-500">
                    {item.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Context Window */}
        <div>
          <div className="mb-2 flex items-center gap-1.5">
            <Activity size={12} className="text-gray-400" strokeWidth={2} />
            <span className="text-[11px] font-medium uppercase tracking-wider text-gray-400">上下文窗口</span>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-200">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                  style={{ width: `${Math.max(percent, 2)}%` }}
                />
              </div>
              <span className="w-8 text-right font-mono text-[10px] text-gray-500">
                {percent.toFixed(0)}%
              </span>
            </div>
            <p className="font-mono text-[10px] text-gray-400">
              {(usedTokens / 1000).toFixed(0)}K / {(maxTokens / 1000).toFixed(0)}K tokens
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[11px] text-gray-400">{label}</span>
      <span className={`text-[11px] text-gray-700 ${mono ? "font-mono" : ""}`}>{value}</span>
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
