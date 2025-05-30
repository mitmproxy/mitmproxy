import { TableHead, TableRow } from "@/components/ui/table";
import * as columns from "./flow-columns";
import { useAppDispatch, useAppSelector } from "web/ducks/hooks";
import { setSort } from "web/ducks/flows";
import { cn } from "@/lib/utils";
import { memo } from "react";
import { useDisplayColumns } from "./use-display-columns";

function FlowTableHeaderRow() {
  const dispatch = useAppDispatch();
  const sortDesc = useAppSelector((state) => state.flows.sort.desc);
  const sortColumn = useAppSelector((state) => state.flows.sort.column);
  const displayColumns = useDisplayColumns();

  const sortType = sortDesc ? "sort-desc" : "sort-asc";

  return (
    <TableRow className="text-xs">
      {displayColumns.map((Column) => (
        <TableHead
          key={Column.name}
          className={cn(sortColumn === Column.name && sortType)}
          // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
          style={columns.getColumnStyle(Column)}
          onClick={() =>
            dispatch(
              setSort({
                column:
                  Column.name === sortColumn && sortDesc
                    ? undefined
                    : Column.name,
                desc: Column.name !== sortColumn ? false : !sortDesc,
              }),
            )
          }
        >
          {Column.headerName}
        </TableHead>
      ))}
    </TableRow>
  );
}

const FlowTableHeaderRowMemo = memo(FlowTableHeaderRow);

export { FlowTableHeaderRowMemo as FlowTableHeaderRow };
