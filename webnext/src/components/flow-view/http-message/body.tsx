import { HttpMessageContentView } from "@/components/content-views";
import type { TabProps } from "@/components/flow-view/panel-tabs";
import type { HTTPFlow } from "web/flow";

export function RequestBody({ flow }: TabProps) {
  return (
    <HttpMessageContentView
      flow={flow as HTTPFlow}
      message={(flow as HTTPFlow).request}
    />
  );
}

export function ResponseBody({ flow }: TabProps) {
  return (
    <HttpMessageContentView
      flow={flow as HTTPFlow}
      message={(flow as HTTPFlow).response!}
    />
  );
}
