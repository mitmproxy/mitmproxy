import type { TabProps } from "@/components/flow-view/panel-tabs";
import {
  KvpTable,
  type KeyValuePair,
  type KeyValuePairs,
} from "@/components/kvp-table";
import type { HTTPFlow } from "web/flow";

export function RequestCookiesTable({ flow }: TabProps) {
  const headers = (flow as HTTPFlow).request.headers;
  const cookieHeaders = extractHeaders(headers, "cookie");

  return (
    <KvpTable
      pairs={cookieHeaders.length > 0 ? parseRequestCookies(cookieHeaders) : []}
    />
  );
}

export function ResponseCookiesTable({ flow }: TabProps) {
  const headers = (flow as HTTPFlow).response?.headers;
  const cookieHeaders = headers ? extractHeaders(headers, "set-cookie") : null;

  return cookieHeaders ? (
    <KvpTable
      pairs={
        cookieHeaders.length > 0 ? parseResponseCookies(cookieHeaders) : []
      }
    />
  ) : null;
}

function extractHeaders(
  headers: [string, string][],
  headerName: string,
): string[] {
  return headers
    .filter((header) => header[0].toLowerCase() === headerName.toLowerCase())
    .map((header) => header[1]);
}

function parseRequestCookies(cookieHeaders: string[]): KeyValuePairs {
  return cookieHeaders.flatMap((header) =>
    header
      .split(";")
      .map((cookie) => cookie.trim().split("=", 2) as KeyValuePair),
  );
}

function parseResponseCookies(cookieHeaders: string[]): KeyValuePairs {
  return cookieHeaders.map((header) => {
    // Split by semicolon and take only the first part (the actual cookie)
    const cookiePart = header.split(";")[0].trim();
    const [key, ...valueParts] = cookiePart.split("=");
    const value = valueParts.join("=");
    return [key, value] as KeyValuePair;
  });
}
