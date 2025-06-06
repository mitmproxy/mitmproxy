import type { TabProps } from "@/components/flow-view/panel-tabs";
import {
  KvpTable,
  type KeyValuePair,
  type KeyValuePairs,
} from "@/components/kvp-table";
import type { HTTPFlow } from "web/flow";

export function CookiesTable({ flow }: TabProps) {
  const cookieHeaders = (flow as HTTPFlow).request.headers
    .filter((header) => header[0].toLowerCase() === "cookie")
    .map((header) => header[1]);

  return (
    <KvpTable
      pairs={cookieHeaders.length > 0 ? parseCookies(cookieHeaders) : []}
    />
  );
}

function parseCookies(cookieHeaders: string[]): KeyValuePairs {
  return cookieHeaders.flatMap((header) =>
    header
      .split(";")
      .map((cookie) => cookie.trim().split("=", 2) as KeyValuePair),
  );
}
