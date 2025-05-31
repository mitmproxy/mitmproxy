import { cn } from "@/lib/utils";
import type { IconBaseProps, IconType } from "react-icons/lib";
import { LuFileText, LuFileCode, LuImage } from "react-icons/lu";
import { SiJavascript } from "react-icons/si";
import type { Flow } from "web/flow";
import { getIcon } from "web/flow/utils";

export function ContentTypeIcon({ flow }: { flow: Flow }) {
  const iconName = getIcon(flow);
  const contentType = iconName.replace("resource-icon-", "");

  let Icon: IconType;

  switch (contentType) {
    case "css":
      Icon = createCustomIcon("CSS");
      break;
    case "quic":
      Icon = createCustomIcon("QUIC");
      break;
    case "websocket":
      Icon = createCustomIcon("WS");
      break;
    case "tcp":
      Icon = createCustomIcon("TCP");
      break;
    case "udp":
      Icon = createCustomIcon("UDP");
      break;
    case "dns":
      Icon = createCustomIcon("DNS");
      break;
    case "redirect":
      Icon = createCustomIcon("30x");
      break;
    case "not-modified":
      Icon = createCustomIcon("304");
      break;
    case "js":
      Icon = SiJavascript;
      break;
    case "document":
      Icon = LuFileCode;
      break;
    case "image":
      Icon = LuImage;
      break;
    case "plain":
    default:
      Icon = LuFileText;
      break;
  }

  return <Icon className="text-muted-foreground" title={contentType} />;
}

function createCustomIcon(text: string) {
  return function CustomTextIcon({ className }: IconBaseProps) {
    return <span className={cn("font-mono", className)}>{text}</span>;
  };
}
