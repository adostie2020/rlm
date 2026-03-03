'use client';

import { Card } from '@/app/components';
import { useChat } from '@ai-sdk/react';
import { TextStreamChatTransport } from 'ai';
import { useState } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';

export default function Page() {
  const { data: session, status: sessionStatus } = useSession();

  if (sessionStatus === 'loading') {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="text-zinc-500 animate-pulse">Loading session...</div>
      </div>
    );
  }

  return <ChatInterface session={session} />;
}

function ChatInterface({ session }: { session: any }) {
  const [input, setInput] = useState('');

  const headers: Record<string, string> = {};
  const user = session?.user as any;
  if (user?.jiraAccessToken) {
    headers['X-Jira-Token'] = user.jiraAccessToken;
  }
  if (user?.jiraCloudId) {
    headers['X-Jira-Resource-Id'] = user.jiraCloudId;
  }

  const { messages, sendMessage, status } = useChat({
    transport: new TextStreamChatTransport({
      api: '/api/chat?protocol=text',
      headers,
    }),
  });
  const scrollToNextSection = () => {
    const sections = Array.from(document.querySelectorAll('section'));
    if (sections.length === 0) return;

    const groups: HTMLElement[][] = [];
    let currentGroup: HTMLElement[] = [];
    let currentRole: string | null = null;

    for (const section of sections) {
      const role = section.getAttribute('data-role');
      if (role !== currentRole && currentGroup.length > 0) {
        groups.push(currentGroup);
        currentGroup = [];
      }
      currentRole = role;
      currentGroup.push(section);
    }
    if (currentGroup.length > 0) {
      groups.push(currentGroup);
    }

    let targetSection = groups[0][0];
    for (const group of groups) {
      const firstSection = group[0];
      const rect = firstSection.getBoundingClientRect();
      if (rect.top > 50) {
        targetSection = firstSection;
        break;
      }
    }

    targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="flex flex-col gap-2">
      {/* Session Debug Panel */}
      <div className="bg-zinc-100 border border-zinc-200 p-2 mx-auto mt-2 w-full max-w-screen-lg md:w-[120ch] text-xs font-mono rounded overflow-hidden">
        <div>Session Jira Token present: {user?.jiraAccessToken ? 'YES' : 'NO'}</div>
        <div>Session Cloud ID: {user?.jiraCloudId || 'NONE'}</div>
        <div className="truncate">Prepared Headers: {JSON.stringify(headers)}</div>
      </div>
      <div className="flex flex-col w-full max-w-screen-lg mx-auto gap-4 p-4 md:w-[120ch]">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3 text-amber-900 text-sm">
          <div className="mt-0.5">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-4 h-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
              />
            </svg>
          </div>
          <div>
            <p className="font-medium">Backend spin-down notice</p>
            <p className="opacity-80">
              This demo uses a render backend that may spin down when inactive.
              Initial requests can take up to 50 seconds to receive.
            </p>
          </div>
        </div>
        {messages.map(message => (
          <section key={message.id} data-role={message.role}>
            <div key={message.id} className="flex flex-row gap-2">
              <div className="flex-shrink-0 w-24 text-zinc-500">{`${message.role}: `}</div>
              <div className="flex flex-col gap-2 whitespace-pre-wrap font-mono overflow-x-auto">
                {message.parts
                  .map(part => (part.type === 'text' ? part.text : ''))
                  .join('')}
              </div>
            </div>
          </section>
        ))}
      </div>

      {messages.length === 0 && <Card type="chat-text" />}

      <form
        onSubmit={e => {
          e.preventDefault();
          sendMessage({ text: input });
          setInput('');
        }}
        className="fixed bottom-0 bg-white flex flex-col w-full border-t"
      >
        <div className="flex justify-between items-center px-4 pt-2">
          <button type="button" onClick={() => scrollToNextSection()} className="text-sm rounded border px-2 py-1 bg-zinc-100/50">
            Go to Next Message
          </button>
          {!session ? (
            <button type="button" onClick={() => signIn('atlassian')} className="text-sm bg-[#0052CC] text-white px-3 py-1 rounded">
              Login with Jira
            </button>
          ) : (
            <div className="flex gap-2 items-center text-sm">
              <span className="text-zinc-500">Authenticated JIRA</span>
              <button type="button" onClick={() => signOut()} className="text-xs text-zinc-400 hover:text-zinc-600">
                Log out
              </button>
            </div>
          )}
        </div>
        <input
          value={input}
          placeholder="Why is the sky blue?"
          onChange={e => setInput(e.target.value)}
          className="w-full p-4 bg-transparent outline-none"
          disabled={status !== 'ready'}
        />
      </form>

    </div>
  );
}
