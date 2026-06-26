"use client";

interface TaskResultProps {
  result: any;
  onReset: () => void;
}

export default function TaskResult({ result, onReset }: TaskResultProps) {
  const isSuccess = result.status === "done";

  return (
    <div
      style={{
        padding: 20,
        backgroundColor: isSuccess ? "#f0fff4" : "#fee",
        border: `1px solid ${isSuccess ? "#28a745" : "#fcc"}`,
        borderRadius: 8,
      }}
    >
      <h3 style={{ margin: "0 0 12px 0", color: isSuccess ? "#28a745" : "#c00" }}>
        {isSuccess ? "✅ 执行成功" : "❌ 执行失败"}
      </h3>

      <pre
        style={{
          whiteSpace: "pre-wrap",
          fontSize: 13,
          backgroundColor: "white",
          padding: 12,
          borderRadius: 6,
          maxHeight: 300,
          overflow: "auto",
        }}
      >
        {JSON.stringify(result, null, 2)}
      </pre>

      <button
        onClick={onReset}
        style={{
          marginTop: 16,
          padding: "10px 20px",
          backgroundColor: "#6c757d",
          color: "white",
          border: "none",
          borderRadius: 6,
          cursor: "pointer",
        }}
      >
        🔄 重新开始
      </button>
    </div>
  );
}
