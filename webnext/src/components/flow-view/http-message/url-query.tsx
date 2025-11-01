import type { TabProps } from "@/components/flow-view/panel-tabs";
import { KvpTable, type KeyValuePair } from "@/components/kvp-table";
import { mainPath } from "web/flow/utils";

export function UrlQueryTable({ flow }: TabProps) {
  const url = mainPath(flow);
  const query = new URLSearchParams(url.split("?")[1] || "");
  const pairs = Array.from(query.entries()).map(
    ([key, value]) => [key, value] satisfies KeyValuePair,
  );

  return <KvpTable pairs={pairs} />;
}
