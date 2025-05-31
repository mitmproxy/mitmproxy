import { MethodBadge } from "@/components/method-badge";
import { StatusBadge } from "@/components/status-badge";
import type { HTTPFlow } from "web/flow";
import { mainPath } from "web/flow/utils";

export function RequestBar({ flow }: { flow: HTTPFlow }) {
  return (
    <div className="flex items-center gap-3">
      <MethodBadge method={flow.request.method} />

      {flow.response?.status_code && (
        <StatusBadge code={flow.response.status_code} />
      )}

      <span className="font-mono text-sm text-blue-600 dark:text-blue-400">
        {mainPath(flow)}
      </span>
    </div>
  );
}
