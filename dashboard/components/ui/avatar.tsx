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
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: "#1a2340",
        border: `2px solid ${color}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.38,
        fontWeight: 600,
        color: "#e2e8f0",
        flexShrink: 0,
      }}
    >
      {getInitials(name)}
    </div>
  );
}
