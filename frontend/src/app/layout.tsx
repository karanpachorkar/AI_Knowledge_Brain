import './globals.css';
import type { Metadata } from 'next';
import TopNavbar from '@/components/TopNavbar';

export const metadata: Metadata = {
  title: 'Glatt AI Knowledge Brain',
  description: 'Enterprise AI Knowledge Brain platform for technical manuals, SOPs, and RAG.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="app-container">
          <TopNavbar />
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
