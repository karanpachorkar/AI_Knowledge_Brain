import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sign In — Glatt AI Knowledge Brain',
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  // No navbar, no sidebar — pure centered auth screen
  return <>{children}</>;
}
