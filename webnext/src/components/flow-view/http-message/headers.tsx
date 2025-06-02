import { useAppSelector } from "web/ducks/hooks";
import type { HTTPFlow } from "web/flow";
import { KvpTable } from "@/components/kvp-table";

export function RequestHeadersTable() {
  const headers = useAppSelector(
    (state) => (state.flows.selected[0] as HTTPFlow).request.headers,
  );

  return <KvpTable pairs={headers} />;
}

export function ResponseHeadersTable() {
  const headers = useAppSelector(
    (state) => (state.flows.selected[0] as HTTPFlow).response?.headers,
  );

  // TODO: add some loading / empty state instead?
  return headers ? <KvpTable pairs={headers} /> : null;
}
