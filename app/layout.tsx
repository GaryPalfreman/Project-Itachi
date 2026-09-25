import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ITACHI",
  description: "ITACHI adaptive intelligence interface",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
