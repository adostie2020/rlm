'use client';

import { Card } from '@/app/components';
import { useChat } from '@ai-sdk/react';
import { TextStreamChatTransport } from 'ai';
import { useState } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';

export default function Page() {
  const [input, setInput] = useState('');
  const { data: session } = useSession();

  const { messages, sendMessage, status } = useChat({
    headers: {
      ...(session?.user?.jiraAccessToken && { 'X-Jira-Token': session.user.jiraAccessToken }),
      ...(session?.user?.jiraCloudId && { 'X-Jira-Resource-Id': session.user.jiraCloudId }),
    },
    transport: new TextStreamChatTransport({
      api: '/api/chat?protocol=text',
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
      <div className="flex flex-col w-full max-w-screen-lg mx-auto gap-2 p-4 md:w-[120ch]">
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
        <button type="button" onClick={() => scrollToNextSection()}>
          Go to Next Message
        </button>
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
