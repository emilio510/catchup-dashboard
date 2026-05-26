interface MessageBubbleProps {
  text: string;
  timestamp?: string;
  side: "left" | "right";
  italic?: boolean;
}

export function MessageBubble({ text, timestamp, side, italic }: MessageBubbleProps) {
  const isLeft = side === "left";

  return (
    <div
      className={`max-w-[85%] ${isLeft ? "mr-auto" : "ml-auto"}`}
    >
      <div
        className={`px-3.5 py-3 ${
          isLeft
            ? "rounded-[10px_10px_10px_2px] border border-[var(--color-border)] bg-[var(--color-bg-elev)]"
            : "rounded-[2px_10px_10px_10px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-card)]"
        }`}
      >
        <div
          className={`whitespace-pre-wrap font-sans text-[13px] leading-[1.6] text-[var(--color-text)] ${
            italic ? "italic" : ""
          }`}
        >
          {text}
        </div>
      </div>
      {timestamp && (
        <div
          className={`mt-1 font-mono text-[10px] text-[var(--color-text-ghost)] ${
            isLeft ? "pl-1 text-left" : "pr-1 text-right"
          }`}
        >
          {timestamp}
        </div>
      )}
    </div>
  );
}
