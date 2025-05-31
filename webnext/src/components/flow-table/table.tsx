import {
  Table,
  TableBody,
  TableHeader,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { useSelector } from "react-redux";
import type { RootState } from "web/ducks/store";
import { TableVirtuoso } from "react-virtuoso";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
} from "@tanstack/react-table";
import { columns } from "./columns";
import { FlowRow } from "./row";
import { useAppDispatch, useAppSelector } from "web/ducks/hooks";
import { setSort } from "web/ducks/flows";
import { LuChevronDown, LuChevronUp } from "react-icons/lu";
import { Button } from "@/components/ui/button";

export function FlowTable() {
  const displayColumnNames = useAppSelector(
    (state) => state.options.web_columns,
  );
  const flowView = useSelector((state: RootState) => state.flows.view);
  const highlightedIds = useSelector(
    (state: RootState) => state.flows.highlightedIds,
  );
  const selectedIds = useSelector(
    (state: RootState) => state.flows.selectedIds,
  );
  const table = useReactTable({
    data: flowView,
    columns: columns.filter(
      // Also include the index column (not the case by default for some reason)
      (col) =>
        col.id && (col.id === "index" || displayColumnNames.includes(col.id)),
    ),
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <TableVirtuoso
      className="h-full w-full"
      data={table.getRowModel().rows}
      components={{
        Table,
        TableBody,
        // eslint-disable-next-line react-x/no-nested-component-definitions
        TableHead: (props) => <TableHeader {...props} className="bg-muted" />,
        // eslint-disable-next-line react-x/no-nested-component-definitions
        TableRow: ({ item: row, ...props }) => (
          <FlowRow
            {...props}
            flow={row.original}
            selected={selectedIds.has(row.original.id)}
            highlighted={highlightedIds.has(row.original.id)}
          />
        ),
      }}
      fixedHeaderContent={function HeadComponent() {
        const dispatch = useAppDispatch();
        const sortDesc = useAppSelector((state) => state.flows.sort.desc);
        const sortColumn = useAppSelector((state) => state.flows.sort.column);

        // TODO: Can we use native tanstack table sorting?
        //       Mitmproxy only supports sorting by one column at a time
        //       so we'd probably need to adapt the sorting logic.

        return (
          <TableRow>
            {table.getHeaderGroups().map((headerGroup) =>
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
                        desc:
                          header.column.id !== sortColumn ? false : !sortDesc,
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
      }}
      itemContent={function CellsComponent(index) {
        const row = table.getRowModel().rows[index];

        return (
          <>
            {row.getVisibleCells().map((cell) => (
              <TableCell
                key={cell.id}
                className="truncate"
                style={{
                  width: cell.column.columnDef.size,
                  minWidth: cell.column.columnDef.size,
                  maxWidth: cell.column.columnDef.size,
                }}
              >
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </TableCell>
            ))}
          </>
        );
      }}
    />
  );
}
