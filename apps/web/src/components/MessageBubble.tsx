"use client";

import { useState } from "react";
import { ChevronRight, Settings, User } from "lucide-react";
import type { ChatMessage } from "@/lib/chatApi";
import Astronaut from "@/components/Astronaut";

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  const [showTool, setShowTool] = useState(false);

  if (message.role === "user") {
    return (
      <div className="flex animate-fade-in items-start justify-end gap-3 py-3">
        <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-gray-100 px-4 py-3 text-[14px] leading-relaxed text-gray-900">
          {message.content}
        </div>
        <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-800 text-white">
          <User size={15} strokeWidth={1.8} />
        </div>
      </div>
    );
  }

  if (message.role === "tool") {
    return (
      <div className="ml-12 animate-fade-in py-1">
        <button
          onClick={() => setShowTool((v) => !v)}
          className="flex items-center gap-1 text-xs text-gray-400 transition hover:text-gray-600"
        >
          <ChevronRight
            size={12}
            className={`transition-transform ${showTool ? "rotate-90" : ""}`}
            strokeWidth={2}
          />
          工具返回
          {message.tool_name && (
            <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-500">
              {message.tool_name}
            </span>
          )}
        </button>
        {showTool && (
          <pre className="mt-1 max-h-40 overflow-auto rounded-lg bg-gray-50 p-3 font-mono text-xs leading-relaxed text-gray-500 ring-1 ring-gray-100">
            {message.content}
          </pre>
        )}
      </div>
    );
  }

  return (
    <div className="flex animate-fade-in items-start gap-3 py-3">
      <div className="mt-0.5 flex-shrink-0">
        <Astronaut size={32} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1.5">
        <span className="text-[11px] font-semibold text-gray-500">DocFlow</span>
        <div className="max-w-full whitespace-pre-wrap rounded-2xl rounded-tl-sm bg-emerald-50 px-4 py-3 text-[14px] leading-relaxed text-gray-800">
          {message.content || "（无内容）"}
        </div>

        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="ml-1 space-y-1">
            {message.tool_calls.map((tc, i) => (
              <div
                key={i}
                className="inline-flex items-center gap-1.5 rounded-lg bg-gray-50 px-2.5 py-1.5 text-xs text-gray-500 ring-1 ring-gray-200/60"
              >
                <Settings size={11} className="text-gray-400" strokeWidth={2} />
                <span className="font-medium text-gray-600">{tc.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
