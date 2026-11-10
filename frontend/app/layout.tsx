import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "VoiceBridge AI · Intent, intact.",
  description: "A synthetic sales-to-engineering intelligence prototype.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
