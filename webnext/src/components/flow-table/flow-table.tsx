/* eslint-disable react-x/no-nested-component-definitions */
import { Table, TableBody, TableHeader } from "../ui/table";
import { useSelector } from "react-redux";
import type { RootState } from "web/ducks/store";
import { FlowRow } from "./flow-row";
import { FlowTableHeaderRow } from "./flow-table-header-row";
import { TableVirtuoso } from "react-virtuoso";
import * as columns from "./flow-columns";
import { useDisplayColumns } from "./use-display-columns";
import type { Flow } from "web/flow";

export function FlowTable() {
  const flowView = useSelector((state: RootState) => state.flows.view);
  const highlightedIds = useSelector(
    (state: RootState) => state.flows.highlightedIds,
  );
  const selectedIds = useSelector(
    (state: RootState) => state.flows.selectedIds,
  );

  return (
    <TableVirtuoso
      className="h-full w-full"
      data={flowView}
      totalCount={flowView.length}
      components={{
        Table: (props) => <Table {...props} />,
        TableHead: (props) => <TableHeader {...props} className="bg-muted" />,
        TableBody: (props) => <TableBody {...props} />,
        TableRow: ({ item: flow, ...props }) => (
          <FlowRow
            key={flow.id}
            {...props}
            flow={flow}
            selected={selectedIds.has(flow.id)}
            highlighted={highlightedIds.has(flow.id)}
          />
        ),
      }}
      fixedHeaderContent={() => <FlowTableHeaderRow />}
      itemContent={(_, flow) => <FlowItemContent flow={flow} />}
    />
  );
}

function FlowItemContent({ flow }: { flow: Flow }) {
  const displayColumns = useDisplayColumns();

  return (
    <>
      {displayColumns.map((Column) => (
        <Column
          key={Column.name}
          flow={flow}
          // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
          style={columns.getColumnStyle(Column)}
        />
      ))}
    </>
  );
}
