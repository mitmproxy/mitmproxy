import { cn } from "@/lib/utils";

interface URLPart {
  text: string;
  color: string;
  label: string;
}

export interface ColoredURLProps {
  url: string;
  className?: string;
}

export function ColoredURL({ url, className }: ColoredURLProps) {
  const urlObj = new URL(url);
  const parts: URLPart[] = [];

  // Protocol.
  if (urlObj.protocol) {
    parts.push({
      text: urlObj.protocol + "//",
      color: "text-muted-foreground",
      label: "Protocol",
    });
  }

  // Username and password (if present).
  if (urlObj.username) {
    let text = urlObj.username;
    if (urlObj.password) {
      text += ":" + urlObj.password;
    }
    parts.push({
      text,
      color: "text-purple-700 dark:text-purple-300",
      label: "Authentication",
    });
    parts.push({
      text: "@",
      color: "text-muted-foreground",
      label: "Authentication",
    });
  }

  // Hostname and port (if present).
  if (urlObj.hostname) {
    let text = urlObj.hostname;
    if (urlObj.port) {
      text += ":" + urlObj.port;
    }
    parts.push({
      text,
      color: "text-blue-700 dark:text-blue-300",
      label: "Hostname",
    });
  }

  // Pathname.
  if (urlObj.pathname) {
    parts.push({
      text: urlObj.pathname,
      color: "text-green-700 dark:text-green-300",
      label: "Path",
    });
  }

  // Search parameters.
  if (urlObj.search) {
    parts.push({
      text: urlObj.search,
      color: "text-orange-700 dark:text-orange-300",
      label: "Query",
    });
  }

  // Hash.
  if (urlObj.hash) {
    parts.push({
      text: urlObj.hash,
      color: "text-amber-700 dark:text-amber-300",
      label: "Fragment",
    });
  }

  return (
    <div
      className={cn("font-mono break-all", className)}
      onMouseDown={(e) => {
        if (e.detail === 3) {
          e.preventDefault();
          const selection = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(e.currentTarget);
          selection?.removeAllRanges();
          selection?.addRange(range);
        }
      }}
    >
      {parts.map((part, index) => (
        <span
          // eslint-disable-next-line react-x/no-array-index-key
          key={index}
          className={cn("hover:bg-muted rounded transition-colors", part.color)}
          title={part.label}
          onMouseDown={(e) => {
            if (e.detail === 2) {
              e.preventDefault();
              const selection = window.getSelection();
              const range = document.createRange();
              range.selectNodeContents(e.currentTarget);
              selection?.removeAllRanges();
              selection?.addRange(range);
            }
          }}
        >
          {part.text}
        </span>
      ))}
    </div>
  );
}
