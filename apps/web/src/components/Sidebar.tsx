"use client";

import { useEffect, useState } from "react";
import { listSessions, createSession, deleteSession } from "@/lib/chatApi";

interface SidebarProps {
  activeSessionId: string | null;
  onSelect: (id: string) => void;
}

export default function Sidebar({ activeSessionId, onSelect }: SidebarProps) {
  const [sessions, setSessions] = useState<{ id: string; title: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      // 静默
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleNew = async () => {
    setLoading(true);
    try {
      const session = await createSession();
      setSessions((prev) => [{ id: session.id, title: session.title }, ...prev]);
      onSelect(session.id);
    } catch (e: any) {
      alert(e.message || "创建会话失败");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) onSelect(null);
    } catch (e: any) {
      alert(e.message || "删除失败");
    }
  };

  return (
    <aside className="flex w-64 flex-shrink-0 flex-col bg-gray-900 text-gray-100">
      {/* Logo / 标题 */}
      <div className="border-b border-gray-700 px-4 py-4">
        <h1 className="text-lg font-semibold">DocFlow Agent</h1>
        <p className="text-xs text-gray-400">对话型 Agent</p>
      </div>

      {/* 新建会话 */}
      <div className="p-3">
        <button
          onClick={handleNew}
          disabled={loading}
          className="w-full rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          + 新建会话
        </button>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {sessions.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-gray-500">
            还没有会话，点击上方按钮新建
          </p>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`group mb-1 flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm transition ${
                activeSessionId === s.id
                  ? "bg-gray-700 text-white"
                  : "text-gray-300 hover:bg-gray-800"
              }`}
            >
              <span className="truncate">{s.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(s.id);
                }}
                className="ml-2 hidden text-gray-400 hover:text-red-400 group-hover:block"
                title="删除"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
