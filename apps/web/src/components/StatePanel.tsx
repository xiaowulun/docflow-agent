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
