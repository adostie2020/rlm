'use client'
import { SessionProvider } from 'next-auth/react';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex-1 flex flex-col pt-12 pb-[120px] bg-zinc-50">
        <SessionProvider>
          {children}
        </SessionProvider>
      </div>
    </div>
  );
}
