"use client";

import { useEffect, useState } from "react";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { listSessions, createSession, deleteSession } from "@/lib/chatApi";
import Astronaut from "@/components/Astronaut";

interface SidebarProps {
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  refreshKey?: number;
}

export default function Sidebar({ activeSessionId, onSelect, onDelete, refreshKey = 0 }: SidebarProps) {
  const [sessions, setSessions] = useState<{ id: string; title: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    try {
      const data = await listSessions();
      setSessions(data);
      return data;
    } catch {
      return [];
    }
  };

  const handleNew = async () => {
    setLoading(true);
    try {
      const session = await createSession();
      setSessions((prev) => [{ id: session.id, title: session.title }, ...prev]);
      onSelect(session.id);
      return session;
    } catch (e: any) {
      alert(e.message || "创建会话失败");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (id: string) => {
    // 通知父组件处理删除（父组件会先清除 activeSessionId 再删除）
    onDelete?.(id);
  };

  useEffect(() => {
    const init = async () => {
      const data = await refresh();
      if (data.length > 0) {
        if (!activeSessionId) onSelect(data[0].id);
      } else {
        await handleNew();
      }
    };
    init();
  }, []);

  useEffect(() => {
    if (refreshKey > 0) refresh();
  }, [refreshKey]);

  return (
    <aside className="flex w-64 flex-shrink-0 flex-col border-r border-gray-200/80 bg-[#f9f9f9] text-gray-700">
      {/* Top: New Chat */}
      <div className="p-3">
        <button
          onClick={handleNew}
          disabled={loading}
          className="flex w-full items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:opacity-40"
        >
          <Plus size={16} strokeWidth={2} />
          新建聊天
        </button>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <p className="px-2 pb-1.5 pt-1 text-[11px] font-medium uppercase tracking-wider text-gray-400">
          聊天记录
        </p>
        {sessions.length === 0 ? (
          <p className="px-2 py-3 text-center text-xs text-gray-400">暂无聊天</p>
        ) : (
          sessions.map((s) => {
            const active = activeSessionId === s.id;
            return (
              <div
                key={s.id}
                onClick={() => onSelect(s.id)}
                className={`group relative mb-0.5 flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] transition ${
                  active
                    ? "bg-gray-200/70 text-gray-900"
                    : "text-gray-600 hover:bg-gray-200/50 hover:text-gray-900"
                }`}
              >
                <MessageSquare size={14} className="flex-shrink-0 text-gray-400" strokeWidth={2} />
                <span className="flex-1 truncate">{s.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(s.id);
                  }}
                  className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded text-gray-400 opacity-0 transition hover:bg-gray-300/50 hover:text-red-500 group-hover:opacity-100"
                >
                  <Trash2 size={13} strokeWidth={2} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Bottom: Profile area */}
      <div className="border-t border-gray-200/80 p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2 transition hover:bg-gray-200/50 cursor-pointer">
          <Astronaut size={32} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium text-gray-800">DocFlow</p>
            <p className="text-[11px] text-gray-400">办公助手</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
