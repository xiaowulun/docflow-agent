import "./globals.css";

export const metadata = {
  title: "DocFlow Agent",
  description: "Conversational agent with tool calling",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-white">{children}</body>
    </html>
  );
}
