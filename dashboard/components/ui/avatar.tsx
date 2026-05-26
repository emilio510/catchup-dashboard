import { PRIORITY_CONFIG, type Priority } from "@/lib/types";

interface AvatarProps {
  name: string;
  priority: Priority;
  size?: number;
}

function getInitials(name: string): string {
  const words = name.split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0][0].toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

export function Avatar({ name, priority, size = 36 }: AvatarProps) {
  const color = PRIORITY_CONFIG[priority].color;
  return (
    <div
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-[var(--color-bg-elev)] font-sans font-semibold text-[var(--color-text)]"
      style={{
        width: size,
        height: size,
        border: `2px solid ${color}`,
        fontSize: Math.round(size * 0.38),
      }}
      aria-label={name}
    >
      {getInitials(name)}
    </div>
  );
}
