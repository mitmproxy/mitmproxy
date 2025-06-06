import type { HTTPFlow } from "web/flow";
import { KvpTable } from "@/components/kvp-table";
import type { TabProps } from "@/components/flow-view/panel-tabs";

export function RequestHeadersTable({ flow }: TabProps) {
  const headers = (flow as HTTPFlow).request.headers;

  return <KvpTable pairs={headers} />;
}

export function ResponseHeadersTable({ flow }: TabProps) {
  const headers = (flow as HTTPFlow).response?.headers;

  // TODO: add some loading / empty state instead?
  return headers ? <KvpTable pairs={headers} /> : null;
}
