"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import StatePanel from "@/components/StatePanel";

export interface SessionInfo {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export default function Home() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [stateRefreshKey, setStateRefreshKey] = useState(0);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50 text-gray-800">
      {/* 左栏：会话历史 */}
      <Sidebar
        activeSessionId={activeSessionId}
        onSelect={(id) => setActiveSessionId(id)}
      />

      {/* 中栏：对话区 */}
      <main className="flex flex-1 flex-col border-x border-gray-200 bg-white">
        <ChatWindow
          sessionId={activeSessionId}
          onMessageSent={() => setStateRefreshKey((k) => k + 1)}
        />
      </main>

      {/* 右栏：state 面板 */}
      <StatePanel sessionId={activeSessionId} refreshKey={stateRefreshKey} />
    </div>
  );
}
