import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://localhost:8000/api/files";

/**
 * 流式代理文件 API：把 /api/files/... 请求转发到后端 8000 端口。
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  // 文件上传：直接转发原始请求体，保留完整的 multipart 数据
  const contentType = request.headers.get("content-type") || "";
  const body = await request.arrayBuffer();

  const res = await fetch(`${BACKEND}/${path}`, {
    method: "POST",
    headers: {
      "content-type": contentType,
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

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  const res = await fetch(`${BACKEND}/${path}`, {
    method: "GET",
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
