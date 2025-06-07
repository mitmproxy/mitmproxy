import { Connection } from "@/components/flow-view/connection";
import { RequestBody } from "@/components/flow-view/http-message/body";
import { RequestCookiesTable } from "@/components/flow-view/http-message/cookies";
import { RequestHeadersTable } from "@/components/flow-view/http-message/headers";
import { UrlQueryTable } from "@/components/flow-view/http-message/url-query";
import { PanelTabs, type Tab } from "./panel-tabs";
import { useAppDispatch } from "web/ducks/hooks";
import { selectRequestTab } from "web/ducks/ui/flow";
import { Timing } from "@/components/flow-view/timing";
import { Comment } from "@/components/flow-view/comment";

export type RequestPanelProps = {
  tab: string;
};

export function RequestPanel({ tab = "headers" }: RequestPanelProps) {
  const dispatch = useAppDispatch();

  return (
    <PanelTabs
      defaultValue={tab}
      onValueChange={(value) => dispatch(selectRequestTab(value))}
      title="Request"
      tabs={tabs}
    />
  );
}

const tabs: Tab[] = [
  {
    name: "Headers",
    value: "headers",
    component: RequestHeadersTable,
    scrollable: true,
  },
  {
    name: "Body",
    value: "body",
    component: RequestBody,
    scrollable: false,
  },
  {
    name: "Query",
    value: "query",
    component: UrlQueryTable,
    scrollable: true,
  },
  {
    name: "Cookies",
    value: "cookies",
    component: RequestCookiesTable,
    scrollable: true,
  },
  {
    name: "Connection",
    value: "connection",
    component: Connection,
    scrollable: true,
  },
  {
    name: "Timing",
    value: "timing",
    component: Timing,
    scrollable: true,
  },
  // TODO: add support for comment field in the response panel too
  {
    name: "Comment",
    value: "comment",
    component: Comment,
    scrollable: true,
  },
];
