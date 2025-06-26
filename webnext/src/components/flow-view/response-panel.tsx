import { ResponseBody } from "@/components/flow-view/http-message/body";
import { ResponseHeadersTable } from "@/components/flow-view/http-message/headers";
import { PanelTabs, type Tab } from "./panel-tabs";
import { useAppDispatch } from "web/ducks/hooks";
import { selectResponseTab } from "web/ducks/ui/flow";
import { ResponseCookiesTable } from "@/components/flow-view/http-message/cookies";

export type ResponsePanelProps = {
  tab: string;
};

export function ResponsePanel({ tab = "headers" }: ResponsePanelProps) {
  const dispatch = useAppDispatch();

  return (
    <PanelTabs
      value={tab}
      onValueChange={(value) => dispatch(selectResponseTab(value))}
      title="Response"
      tabs={tabs}
    />
  );
}

const tabs: Tab[] = [
  {
    name: "Headers",
    value: "headers",
    component: ResponseHeadersTable,
    scrollable: true,
  },
  {
    name: "Body",
    value: "body",
    component: ResponseBody,
    scrollable: false,
  },
  {
    name: "Set-Cookie",
    value: "set-cookie",
    component: ResponseCookiesTable,
    scrollable: true,
  },
];
