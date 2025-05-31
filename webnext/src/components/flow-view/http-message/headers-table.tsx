import { useAppSelector } from "web/ducks/hooks";
import type { HTTPFlow } from "web/flow";
import { KvpTable } from "@/components/kvp-table";

export function HeadersTable() {
  const headers = useAppSelector((state) => state.flows.selected[0] as HTTPFlow)
    .request.headers;

  return <KvpTable pairs={headers} />;
}
