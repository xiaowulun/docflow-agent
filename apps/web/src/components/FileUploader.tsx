"use client";

import { useRef } from "react";

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
}

export default function FileUploader({
  onFileSelect,
  selectedFile,
}: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <label style={{ display: "block", marginBottom: 8, fontWeight: "bold" }}>
        文件
      </label>

      <div
        onClick={handleClick}
        style={{
          padding: 20,
          border: "2px dashed #ddd",
          borderRadius: 8,
          textAlign: "center",
          cursor: "pointer",
          backgroundColor: selectedFile ? "#f0fff4" : "#fafafa",
          borderColor: selectedFile ? "#28a745" : "#ddd",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".docx,.doc,.xlsx,.xls,.pdf"
          onChange={handleChange}
          style={{ display: "none" }}
        />

        {selectedFile ? (
          <div>
            <div style={{ fontSize: 14, color: "#28a745", marginBottom: 4 }}>
              ✅ 已选择文件
            </div>
            <div style={{ fontWeight: "bold" }}>{selectedFile.name}</div>
            <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
              {formatSize(selectedFile.size)}
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 14, color: "#666", marginBottom: 4 }}>
              📄 点击选择文件
            </div>
            <div style={{ fontSize: 12, color: "#999" }}>
              支持 Word (.docx)、Excel (.xlsx)、PDF (.pdf)
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
