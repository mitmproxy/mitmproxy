import { MethodBadge } from "@/components/method-badge";
import { StatusBadge } from "@/components/status-badge";
import type { HTTPFlow } from "web/flow";
import { mainPath } from "web/flow/utils";

export function HttpBar({ flow }: { flow: HTTPFlow }) {
  return (
    <div className="flex flex-col items-start gap-3 lg:flex-row">
      <div className="flex shrink-0 items-center gap-3">
        <MethodBadge method={flow.request.http_version} />
        <MethodBadge method={flow.request.method} />
        {flow.response?.status_code && (
          <StatusBadge code={flow.response.status_code} />
        )}
      </div>

      <div>
        <span className="font-mono text-sm break-all text-blue-600 dark:text-blue-400">
          {mainPath(flow)}
        </span>
      </div>
    </div>
  );
}
