"use client";

import { useEffect, useRef, useState } from "react";
import {
  getSession,
  sendMessage,
  type SessionDetail,
  type ChatMessage,
} from "@/lib/chatApi";
import MessageBubble from "@/components/MessageBubble";

interface ChatWindowProps {
  sessionId: string | null;
  onMessageSent?: () => void;
}

export default function ChatWindow({ sessionId, onMessageSent }: ChatWindowProps) {
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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
  }, [session?.messages, sending]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !sessionId || sending) return;

    setInput("");
    setSending(true);

    // 乐观：先在本地追加用户消息
    const optimistic: ChatMessage = {
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setSession((prev) =>
      prev
        ? { ...prev, messages: [...prev.messages, optimistic], status: "thinking" }
        : prev
    );

    try {
      await sendMessage(sessionId, text);
      refresh();
      onMessageSent?.();
    } catch (e: any) {
      setSession((prev) =>
        prev ? { ...prev, status: "error" } : prev
      );
      alert(e.message || "发送失败");
      refresh();
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* 顶栏 */}
      <div className="flex items-center justify-between border-b border-gray-200 px-6 py-3">
        <h2 className="text-sm font-medium text-gray-700">
          {session ? session.title : "未选择会话"}
        </h2>
        {session && (
          <span className="text-xs text-gray-400">{session.model}</span>
        )}
      </div>

      {/* 消息流 */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {!session ? (
          <EmptyHint />
        ) : session.messages.length === 0 && !sending ? (
          <div className="flex h-full items-center justify-center text-center text-sm text-gray-400">
            发送一条消息开始对话
          </div>
        ) : (
          <div className="space-y-4">
            {session.messages.map((m, i) => (
              <MessageBubble key={i} message={m} />
            ))}
            {sending && (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
                agent 正在思考...
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!sessionId || sending}
            placeholder={sessionId ? "输入消息，Enter 发送，Shift+Enter 换行" : "请先在左侧选择或新建会话"}
            rows={1}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 disabled:bg-gray-50"
          />
          <button
            onClick={handleSend}
            disabled={!sessionId || sending || !input.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-40"
          >
            发送
          </button>
        </div>
      </div>
    </>
  );
}

function EmptyHint() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center text-gray-400">
      <div className="mb-3 text-4xl">💬</div>
      <p className="text-sm">从左侧选择一个会话，或点击「新建会话」开始</p>
    </div>
  );
}
