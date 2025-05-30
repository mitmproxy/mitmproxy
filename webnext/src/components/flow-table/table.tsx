import {
  Table,
  TableBody,
  TableHeader,
  TableRow,
  TableHead,
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
import { Fragment } from "react";

export function FlowTable() {
  const flowView = useSelector((state: RootState) => state.flows.view);
  const highlightedIds = useSelector(
    (state: RootState) => state.flows.highlightedIds,
  );
  const selectedIds = useSelector(
    (state: RootState) => state.flows.selectedIds,
  );
  const table = useReactTable({
    data: flowView,
    columns,
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

        return (
          <TableRow>
            {table.getHeaderGroups().map((headerGroup) =>
              headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  style={{ width: header.getSize() }}
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
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
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
              <Fragment key={cell.id}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </Fragment>
            ))}
          </>
        );
      }}
    />
  );
}
