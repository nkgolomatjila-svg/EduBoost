import "./globals.css";

export const metadata = {
  title: "EduBoost SA",
  description: "AI-powered learning for South African learners Grade R to Grade 7",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
