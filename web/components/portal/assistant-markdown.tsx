"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function AssistantMarkdown({ content }: { content: string }) {
  return (
    <div className="chat-markdown">
      <Markdown
        remarkPlugins={[remarkGfm]}
        allowedElements={["p", "ul", "ol", "li", "strong", "em", "code", "a"]}
        unwrapDisallowed
      >
        {content}
      </Markdown>
    </div>
  );
}
