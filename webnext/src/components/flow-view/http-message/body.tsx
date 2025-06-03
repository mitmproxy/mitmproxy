import {
  HttpMessageContentView,
  type HttpMessageContentViewProps,
} from "@/components/content-views";
import { useAppSelector } from "web/ducks/hooks";
import type { HTTPFlow } from "web/flow";

export function Body({ type }: { type: HttpMessageContentViewProps["part"] }) {
  const flow = useAppSelector((state) => state.flows.selected[0] as HTTPFlow);

  return <HttpMessageContentView flow={flow} part={type} />;
}

export function RequestBody() {
  return <Body type="request" />;
}

export function ResponseBody() {
  return <Body type="response" />;
}
