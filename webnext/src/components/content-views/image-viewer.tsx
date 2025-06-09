import type { HTTPFlow, HTTPMessage } from "web/flow";
import { MessageUtils } from "web/flow/utils";

type ImageViewerProps = {
  flow: HTTPFlow;
  message: HTTPMessage;
  className?: string;
};

export function ImageViewer({ flow, message, className }: ImageViewerProps) {
  return (
    <img
      src={MessageUtils.getContentURL(flow, message)}
      alt="preview"
      className={className}
    />
  );
}

export function isImage(message: HTTPMessage) {
  const regex =
    /^image\/(png|jpe?g|gif|webp|vnc.microsoft.icon|x-icon|svg\+xml)$/i;
  return regex.test(MessageUtils.getContentType(message) || "");
}
