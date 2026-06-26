"use client";

import { useEffect, useState } from "react";
import { getSession, type SessionDetail } from "@/lib/chatApi";

interface StatePanelProps {
  sessionId: string | null;
  // 刷新触发器：每次发消息后递增，触发重新拉取
  refreshKey?: number;
}

export default function StatePanel({ sessionId, refreshKey = 0 }: StatePanelProps) {
  const [session, setSession] = useState<SessionDetail | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      return;
    }
    getSession(sessionId)
      .then(setSession)
      .catch(() => setSession(null));
  }, [sessionId, refreshKey]);

  const statusColor = (status?: string) => {
    switch (status) {
      case "thinking":
        return "text-amber-600 bg-amber-50";
      case "calling_tool":
        return "text-blue-600 bg-blue-50";
<<<<<<< HEAD
      case "awaiting_confirmation":
        return "text-violet-600 bg-violet-50";
      case "saving":
        return "text-emerald-600 bg-emerald-50";
=======
>>>>>>> origin/main
      case "error":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  return (
    <aside className="flex w-72 flex-shrink-0 flex-col bg-white">
      <div className="border-b border-gray-200 px-4 py-4">
        <h2 className="text-sm font-semibold text-gray-700">Session State</h2>
      </div>

      {!session ? (
        <div className="flex flex-1 items-center justify-center px-4 text-center text-xs text-gray-400">
          选择一个会话查看状态
        </div>
      ) : (
        <div className="flex-1 space-y-4 overflow-y-auto p-4 text-sm">
          {/* 状态徽章 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">状态</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(
                session.status
              )}`}
            >
              {session.status}
            </span>
          </div>

          {/* 元数据 */}
          <Info label="Session ID" value={session.id} mono />
          <Info
            label="消息数"
            value={String(session.messages?.length ?? 0)}
          />
          <Info label="当前模型" value={session.model} mono />
          <Info label="创建时间" value={formatTime(session.createdAt)} />
          <Info label="更新时间" value={formatTime(session.updatedAt)} />

<<<<<<< HEAD
          <Info
            label="内容数"
            value={String(session.contents?.length ?? 0)}
          />

          {session.status === "awaiting_confirmation" && (
            <div className="rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-700">
              当前有草稿待确认，用户可以继续要求保存，默认格式为 md。
            </div>
          )}

=======
>>>>>>> origin/main
          {/* 可用工具 */}
          <div>
            <p className="mb-1 text-xs text-gray-500">可用工具</p>
            <div className="flex flex-wrap gap-1">
              {(session.tools ?? []).map((t) => (
                <span
                  key={t.name}
                  className="rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
                  title={t.description}
                >
                  {t.name}
                </span>
              ))}
              {(session.tools ?? []).length === 0 && (
                <span className="text-xs text-gray-400">无</span>
              )}
            </div>
          </div>
<<<<<<< HEAD

          <div>
            <p className="mb-1 text-xs text-gray-500">当前内容</p>
            <div className="space-y-2">
              {(session.contents ?? []).map((item) => (
                <div
                  key={item.id}
                  className="rounded border border-gray-200 bg-gray-50 px-2 py-2 text-xs text-gray-700"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-gray-800">{item.title}</span>
                    <span
                      className={`rounded px-1.5 py-0.5 ${
                        item.is_saved
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {item.is_saved ? `已保存 ${item.output_format}` : "草稿"}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-3 whitespace-pre-wrap text-gray-600">
                    {item.content}
                  </p>
                </div>
              ))}
              {(session.contents ?? []).length === 0 && (
                <span className="text-xs text-gray-400">暂无内容</span>
              )}
            </div>
          </div>
=======
>>>>>>> origin/main
        </div>
      )}
    </aside>
  );
}

function Info({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="mb-0.5 text-xs text-gray-500">{label}</p>
      <p
        className={`break-all text-xs text-gray-800 ${
          mono ? "font-mono" : ""
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
}
