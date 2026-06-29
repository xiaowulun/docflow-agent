"use client";

import { useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import StatePanel from "@/components/StatePanel";
import { deleteSession } from "@/lib/chatApi";

export interface SessionInfo {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export default function Home() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [stateRefreshKey, setStateRefreshKey] = useState(0);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);

  const handleMessageSent = useCallback(() => {
    setStateRefreshKey((k) => k + 1);
    setSidebarRefreshKey((k) => k + 1);
  }, []);

  const handleDeleteSession = useCallback(
    async (deletedId: string) => {
      // 1. 先清除活跃会话 ID，让 ChatWindow 停止请求
      setActiveSessionId(null);
      // 2. 再执行删除
      try {
        await deleteSession(deletedId);
      } catch {
        // 忽略
      }
      // 3. 刷新侧边栏
      setSidebarRefreshKey((k) => k + 1);
    },
    []
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-gray-800">
      <Sidebar
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onDelete={handleDeleteSession}
        refreshKey={sidebarRefreshKey}
      />
      <ChatWindow
        sessionId={activeSessionId}
        onMessageSent={handleMessageSent}
      />
      <StatePanel sessionId={activeSessionId} refreshKey={stateRefreshKey} />
    </div>
  );
}
