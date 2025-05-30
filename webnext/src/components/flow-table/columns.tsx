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
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import * as flowActions from "web/ducks/flows";
import { CircleAlert, Lock, LockOpen } from "lucide-react";

export const columns: ColumnDef<Flow>[] = [
  {
    id: "tls",
    header: "",
    size: 20,
    //minSize: 8,
    //maxSize: 8,
    cell: function CellComponent({ row }) {
      const isTLS = row.original.client_conn.tls_established;

      return (
        <div title={isTLS ? "Client TLS connection established" : "No TLS"}>
          {isTLS ? (
            <Lock className="text-muted-foreground size-4" />
          ) : (
            <LockOpen className="text-muted-foreground size-4" />
          )}
        </div>
      );
    },
  },
  {
    id: "index",
    accessorKey: "index",
    header: "#",
    size: 60,
    minSize: 40,
    maxSize: 80,
    cell: function CellComponent({ row }) {
      const index = useAppSelector((state) =>
        state.flows._listIndex.get(row.original.id),
      );

      return (index ?? 0) + 1;
    },
  },
  {
    id: "icon",
    header: "",
    size: 40,
    minSize: 40,
    maxSize: 50,
    cell: function CellComponent() {
      // TODO: implement icons
      return "icon";
    },
  },
  {
    id: "path",
    header: "Path",
    size: 300,
    minSize: 150,
    maxSize: 500,
    cell: function CellComponent({ row }) {
      // TODO: implement flow.marked

      const isError = Boolean(row.original.error);

      return (
        <div className="relative">
          <span className="block truncate pr-6">{mainPath(row.original)}</span>

          {isError && (
            <div
              title={`Error: ${row.original.error?.msg ?? "unknown connection error"}`}
            >
              <CircleAlert className="absolute top-1/2 right-0 size-4 -translate-y-1/2 text-red-500" />
            </div>
          )}
        </div>
      );
    },
  },
  {
    id: "method",
    header: "Method",
    size: 70,
    minSize: 60,
    maxSize: 80,
    cell: function CellComponent({ row }) {
      return (
        <Badge variant="outline" className="h-4 px-1 text-xs">
          {getMethod(row.original)}
        </Badge>
      );
    },
  },
  {
    id: "version",
    header: "Version",
    size: 80,
    minSize: 60,
    maxSize: 100,
    cell: function CellComponent({ row }) {
      return getVersion(row.original);
    },
  },
  {
    id: "status",
    header: "Status",
    size: 70,
    minSize: 60,
    maxSize: 80,
    cell: function CellComponent({ row }) {
      const flow = row.original;

      if (flow.type === "dns" && flow.response) {
        return <Badge>{flow.response.response_code}</Badge>;
      }

      if (flow.type === "http" && flow.response) {
        return <StatusBadge code={flow.response.status_code} />;
      }

      return null;
    },
  },
  {
    id: "size",
    header: "Size",
    size: 80,
    minSize: 70,
    maxSize: 100,
    cell: function CellComponent({ row }) {
      return formatSize(getTotalSize(row.original));
    },
  },
  {
    id: "time",
    header: "Time",
    size: 80,
    minSize: 70,
    maxSize: 100,
    cell: function CellComponent({ row }) {
      const start = startTime(row.original);
      const end = endTime(row.original);

      return start && end ? formatTimeDelta(1000 * (end - start)) : "...";
    },
  },
  {
    id: "timestamp",
    header: "Timestamp",
    size: 150,
    minSize: 120,
    maxSize: 180,
    cell: function CellComponent({ row }) {
      const time = startTime(row.original);

      return time ? formatTimeStamp(time) : "...";
    },
  },
  {
    id: "quickactions",
    header: "Actions",
    size: 90,
    minSize: 80,
    maxSize: 120,
    cell: function CellComponent({ row }) {
      const dispatch = useAppDispatch();
      const flow = row.original;

      if (flow.intercepted) {
        return (
          <Button
            size="sm"
            onClick={() => void dispatch(flowActions.resume([flow]))}
          >
            Resume
          </Button>
        );
      }

      if (canReplay(flow)) {
        return (
          <Button
            size="sm"
            onClick={() => void dispatch(flowActions.replay([flow]))}
          >
            Replay
          </Button>
        );
      }

      return null;
    },
  },
  {
    id: "comment",
    header: "Comment",
    size: 200,
    minSize: 100,
    maxSize: 300,
    cell: function CellComponent({ row }) {
      const text = row.original.comment;

      return text;
    },
  },
];
