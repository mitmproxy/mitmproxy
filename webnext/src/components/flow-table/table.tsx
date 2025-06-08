import {
  Table,
  TableBody,
  TableHeader,
  TableRow,
  TableHead,
  TableCell,
  type TableHeaderProps,
  type TableRowProps,
} from "@/components/ui/table";
import { useSelector } from "react-redux";
import type { RootState } from "web/ducks/store";
import { TableVirtuoso } from "react-virtuoso";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type HeaderGroup,
  type Row,
} from "@tanstack/react-table";
import { columns } from "./columns";
import { FlowRow } from "./row";
import { useAppDispatch, useAppSelector } from "web/ducks/hooks";
import { setSort } from "web/ducks/flows";
import { LuChevronDown, LuChevronUp } from "react-icons/lu";
import { Button } from "@/components/ui/button";
import type { Flow } from "web/flow";
import React from "react";

export function FlowTable() {
  // Prevent the react compiler from memoizing this component to circumvent list state issues with the TableVirtuoso component.
  // eslint-disable-next-line react-compiler/react-compiler -- this is most likely a bug in the react-compiler plugin
  "use no memo";

  const displayColumnNames = useAppSelector(
    (state) => state.options.web_columns,
  );
  const flowView = useSelector((state: RootState) => state.flows.view);
  const filteredColumns = columns.filter(
    // Also include the index column (not the case by default for some reason)
    (col) =>
      col.id && (col.id === "index" || displayColumnNames.includes(col.id)),
  );
  const table = useReactTable({
    data: flowView,
    columns: filteredColumns,
    getCoreRowModel: getCoreRowModel(),
    autoResetAll: false,
  });

  const { rows } = table.getRowModel();
  const headerGroups = table.getHeaderGroups();

  return (
    <TableVirtuoso
      className="h-full w-full"
      data={rows}
      computeItemKey={(_, v) => v.original.id}
      followOutput={true}
      fixedItemHeight={43}
      components={{
        Table,
        TableBody,
        TableHead: TableHeadComponent,
        TableRow: TableRowComponent,
      }}
      fixedHeaderContent={() => (
        <FixedHeaderContent headerGroups={headerGroups} />
      )}
      itemContent={(_, row) => <ItemContent row={row} />}
    />
  );
}

function FixedHeaderContent({
  headerGroups,
}: {
  headerGroups: HeaderGroup<Flow>[];
}) {
  const dispatch = useAppDispatch();
  const sortDesc = useAppSelector((state) => state.flows.sort.desc);
  const sortColumn = useAppSelector((state) => state.flows.sort.column);

  // TODO: Can we use native tanstack table sorting?
  //       Mitmproxy only supports sorting by one column at a time
  //       so we'd probably need to adapt the sorting logic.

  return (
    <TableRow>
      {headerGroups.map((headerGroup) =>
        headerGroup.headers.map((header) => (
          <TableHead
            key={header.id}
            style={{
              width: header.column.columnDef.size,
              minWidth: header.column.columnDef.minSize,
              maxWidth: header.column.columnDef.maxSize,
            }}
            onClick={() =>
              dispatch(
                setSort({
                  column:
                    header.column.id === sortColumn && sortDesc
                      ? undefined
                      : // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        (header.column.id as any),
                  desc: header.column.id !== sortColumn ? false : !sortDesc,
                }),
              )
            }
          >
            <Button
              variant="ghost"
              className="flex w-full justify-between gap-2 p-0"
            >
              {header.isPlaceholder
                ? null
                : flexRender(
                    header.column.columnDef.header,
                    header.getContext(),
                  )}
              <div className="size-4">
                {sortColumn === header.column.id && (
                  <>{sortDesc ? <LuChevronDown /> : <LuChevronUp />}</>
                )}
              </div>
            </Button>
          </TableHead>
        )),
      )}
    </TableRow>
  );
}

const ItemContent = function ItemContent({ row }: { row: Row<Flow> }) {
  return (
    <React.Fragment key={row.id}>
      {row.getVisibleCells().map((cell) => (
        <TableCell
          key={cell.id}
          className="truncate"
          style={{
            width: cell.column.columnDef.size,
            minWidth: cell.column.columnDef.minSize,
            maxWidth: cell.column.columnDef.maxSize,
          }}
        >
          {flexRender(cell.column.columnDef.cell, cell.getContext())}
        </TableCell>
      ))}
    </React.Fragment>
  );
};

function TableHeadComponent(props: TableHeaderProps) {
  return <TableHeader {...props} className="bg-muted" />;
}

function TableRowComponent({
  className,
  item: row,
  ...props
}: TableRowProps & { item: Row<Flow> }) {
  const highlightedIds = useSelector(
    (state: RootState) => state.flows.highlightedIds,
  );
  const selectedIds = useSelector(
    (state: RootState) => state.flows.selectedIds,
  );

  return (
    <FlowRow
      key={row.id}
      {...props}
      flow={row.original}
      selected={selectedIds.has(row.original.id)}
      highlighted={highlightedIds.has(row.original.id)}
    />
  );
}
