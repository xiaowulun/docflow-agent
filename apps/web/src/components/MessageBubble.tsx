"use client";

import { useState } from "react";
import type { ChatMessage } from "@/lib/chatApi";

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  const [showTool, setShowTool] = useState(false);

  // user 消息靠右
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  // tool 消息：折叠展示工具返回结果
  if (message.role === "tool") {
    return (
      <div className="ml-2">
        <button
          onClick={() => setShowTool((v) => !v)}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          {showTool ? "▼" : "▶"} 工具返回
          {message.tool_name ? `（${message.tool_name}）` : ""}
        </button>
        {showTool && (
          <pre className="mt-1 max-h-40 overflow-auto rounded bg-gray-100 p-2 text-xs text-gray-700">
            {message.content}
          </pre>
        )}
      </div>
    );
  }

  // assistant 消息靠左
  return (
    <div className="flex flex-col items-start gap-1">
      <div className="max-w-[75%] whitespace-pre-wrap rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2 text-sm text-gray-800">
        {message.content || "（无内容）"}
      </div>

      {/* 如果这条 assistant 消息触发了工具调用，展示调用过程 */}
      {message.tool_calls && message.tool_calls.length > 0 && (
        <div className="ml-1 space-y-1">
          {message.tool_calls.map((tc, i) => (
            <div
              key={i}
              className="rounded border border-blue-200 bg-blue-50 px-2 py-1 text-xs text-blue-700"
            >
              🔧 {tc.name}
              <span className="ml-1 text-blue-400">
                {JSON.stringify(tc.arguments)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
