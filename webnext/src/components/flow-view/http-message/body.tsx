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
  const response = (flow as HTTPFlow).response;

  return response ? (
    <HttpMessageContentView flow={flow as HTTPFlow} message={response} />
  ) : null;
}
