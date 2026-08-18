"use client";

import { useEffect, useRef } from "react";
import dynamic from "next/dynamic";

import type { ChatMessage } from "@/lib/api/types";

const AssistantMarkdown = dynamic(() => import("./assistant-markdown"), {
  ssr: false,
});

export function ChatBubble({ message }: { message: ChatMessage }) {
  const isCustomer = message.role === "customer";
  const isHuman = message.role === "human_agent";
  const align = isCustomer ? "justify-end" : "justify-start";
  const tone = isCustomer
    ? "bg-[var(--accent)] text-[var(--accent-ink)]"
    : isHuman
      ? "bg-[#dfe8f5] text-[#1c1915]"
      : "bg-[#f6efe4] text-[var(--ink)]";

  return (
    <div className={`flex ${align}`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${tone}`}>
        {message.role === "assistant" ? (
          <AssistantMarkdown content={message.content} />
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
      </div>
    </div>
  );
}

export function ChatTranscript({ messages }: { messages: ChatMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  return (
    <div className="grid gap-3">
      {messages.map((message) => (
        <ChatBubble key={message.id} message={message} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
