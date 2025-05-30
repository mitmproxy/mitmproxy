import type { ColumnDef } from "@tanstack/react-table";
import { useAppDispatch, useAppSelector } from "web/ducks/hooks";
import type { Flow } from "web/flow";
import {
  canReplay,
  endTime,
  getMethod,
  getTotalSize,
  getVersion,
  mainPath,
  startTime,
} from "web/flow/utils";
import { Badge } from "@/components/ui/badge";
import { formatSize, formatTimeDelta, formatTimeStamp } from "web/utils";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import * as flowActions from "web/ducks/flows";
import { TableCell } from "@/components/ui/table";

export const columns: ColumnDef<Flow>[] = [
  {
    id: "tls",
    header: "",
    size: 5,
    cell: function CellComponent({ row }) {
      const isTLS = row.original.client_conn.tls_established;

      return (
        <TableCell
          className={cn("border-l-4", { "border-l-green-500": isTLS })}
        />
      );
    },
  },
  {
    accessorKey: "index",
    header: "#",
    cell: function CellComponent({ row }) {
      const index = useAppSelector((state) =>
        state.flows._listIndex.get(row.original.id),
      );

      return <TableCell>{(index ?? 0) + 1}</TableCell>;
    },
  },
  {
    id: "icon",
    header: "",
    size: 20,
    cell: function CellComponent() {
      // TODO: implement icons
      return <TableCell>icon</TableCell>;
    },
  },
  {
    id: "path",
    header: "Path",
    size: 100,
    cell: function CellComponent({ row }) {
      // TODO: implement flow.error
      // TODO: implement flow.marked

      return (
        <TableCell
          className={cn("truncate", {
            "bg-red-500": row.original.error,
          })}
        >
          {mainPath(row.original)}
        </TableCell>
      );
    },
  },
  {
    id: "method",
    header: "Method",
    size: 50,
    cell: function CellComponent({ row }) {
      return (
        <TableCell>
          <Badge variant="outline" className="h-4 px-1 text-xs">
            {getMethod(row.original)}
          </Badge>
        </TableCell>
      );
    },
  },
  {
    id: "version",
    header: "Version",
    cell: function CellComponent({ row }) {
      return <TableCell>{getVersion(row.original)}</TableCell>;
    },
  },
  {
    id: "status",
    header: "Status",
    size: 50,
    cell: function CellComponent({ row }) {
      const flow = row.original;

      if (flow.type === "dns" && flow.response) {
        return (
          <TableCell>
            <Badge>{flow.response.response_code}</Badge>
          </TableCell>
        );
      }

      if (flow.type === "http" && flow.response) {
        return (
          <TableCell>
            <StatusBadge code={flow.response.status_code} />
          </TableCell>
        );
      }

      return <TableCell></TableCell>;
    },
  },
  {
    id: "size",
    header: "Size",
    size: 80,
    cell: function CellComponent({ row }) {
      return <TableCell>{formatSize(getTotalSize(row.original))}</TableCell>;
    },
  },
  {
    id: "time",
    header: "Time",
    size: 80,
    cell: function CellComponent({ row }) {
      const start = startTime(row.original);
      const end = endTime(row.original);

      return (
        <TableCell>
          {start && end ? formatTimeDelta(1000 * (end - start)) : "..."}
        </TableCell>
      );
    },
  },
  {
    id: "timestamp",
    header: "Timestamp",
    size: 150,
    cell: function CellComponent({ row }) {
      const time = startTime(row.original);

      return <TableCell>{time ? formatTimeStamp(time) : "..."}</TableCell>;
    },
  },
  {
    id: "quickactions",
    header: "Actions",
    cell: function CellComponent({ row }) {
      const dispatch = useAppDispatch();
      const flow = row.original;

      if (flow.intercepted) {
        return (
          <TableCell>
            <Button
              size="sm"
              onClick={() => void dispatch(flowActions.resume([flow]))}
            >
              Resume
            </Button>
          </TableCell>
        );
      }

      if (canReplay(flow)) {
        return (
          <TableCell>
            <Button
              size="sm"
              onClick={() => void dispatch(flowActions.replay([flow]))}
            >
              Replay
            </Button>
          </TableCell>
        );
      }

      return <TableCell />;
    },
  },
  {
    id: "comment",
    header: "Comment",
    cell: function CellComponent({ row }) {
      const text = row.original.comment;

      return <TableCell>{text}</TableCell>;
    },
  },
];
