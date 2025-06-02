import { KvpTable, type KeyValuePair } from "@/components/kvp-table";
import { useAppSelector } from "web/ducks/hooks";
import { mainPath } from "web/flow/utils";

export function UrlQueryTable() {
  const flow = useAppSelector((state) => state.flows.selected[0]);
  const url = mainPath(flow);
  const query = new URLSearchParams(url.split("?")[1] || "");
  const pairs = Array.from(query.entries()).map(
    ([key, value]) => [key, value] satisfies KeyValuePair,
  );

  return <KvpTable pairs={pairs} />;
}
