import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://localhost:8000/api/chat";

/**
 * 流式代理：把 /api/chat/... 请求转发到后端 8000 端口。
 * 对 SSE 流式接口（/messages/stream）保持流式转发，不 buffer。
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const body = await request.text();

  const res = await fetch(`${BACKEND}/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body,
  });

  // 如果是 SSE 流式响应，直接透传 stream
  if (res.headers.get("content-type")?.includes("text/event-stream")) {
    return new NextResponse(res.body, {
      status: res.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  // 普通 JSON 响应
  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") || "application/json",
    },
  });
}

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  const res = await fetch(`${BACKEND}/${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") || "application/json",
    },
  });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  const res = await fetch(`${BACKEND}/${path}`, {
    method: "DELETE",
  });

  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") || "application/json",
    },
  });
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const body = await request.text();

  const res = await fetch(`${BACKEND}/${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body,
  });

  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") || "application/json",
    },
  });
}
