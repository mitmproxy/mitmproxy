import {
  HttpMessageContentView,
  type HttpMessageContentViewProps,
} from "@/components/content-views";
import type { TabProps } from "@/components/flow-view/panel-tabs";
import type { HTTPFlow } from "web/flow";

export function Body({
  type,
  flow,
}: { type: HttpMessageContentViewProps["part"] } & TabProps) {
  return <HttpMessageContentView flow={flow as HTTPFlow} part={type} />;
}

export function RequestBody(props: TabProps) {
  return <Body {...props} type="request" />;
}

export function ResponseBody(props: TabProps) {
  return <Body {...props} type="response" />;
}
