import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Enterprise AI Knowledge Platform',
  description: 'Generic, secure, multi-tenant enterprise AI RAG platform.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="layout-container">
          <aside className="sidebar">
            <div className="brand-header">
              <div className="brand-logo">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              </div>
              <span className="brand-title">Enterprise AI</span>
            </div>

            <nav>
              <ul className="nav-menu">
                <li><a className="nav-item active" href="#">Dashboard</a></li>
                <li><a className="nav-item" href="#">Knowledge Bases</a></li>
                <li><a className="nav-item" href="#">Documents</a></li>
                <li><a className="nav-item" href="#">Chat Workspace</a></li>
                <li><a className="nav-item" href="#">AI Model Gateway</a></li>
                <li><a className="nav-item" href="#">Users & Roles</a></li>
                <li><a className="nav-item" href="#">Audit & Security</a></li>
                <li><a className="nav-item" href="#">System Settings</a></li>
              </ul>
            </nav>
          </aside>

          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
