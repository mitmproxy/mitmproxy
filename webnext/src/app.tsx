import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Header } from "@/components/header";
import { SideMenu } from "./components/sidemenu";
import { ThemeToggle } from "./components/theme-toggle";
import { FilterPanel } from "./components/filter-panel";
import { FlowTable } from "./components/flow-table";
import { RequestDetails } from "./components/request-details";
import { ResponseDetails } from "./components/response-details";
import { Footer } from "./components/footer";
import { useDispatch, useSelector } from "react-redux";
import type { RootState } from "web/ducks/store";
import { onKeyDown } from "web/ducks/ui/keyboard";

const mockFlows = [
  {
    id: 85,
    url: "https://www.producthunt.com/frontend/graphql",
    origin: "Google Chrome",
    method: "POST",
    status: "Completed",
    code: 200,
    time: "14:23:28.801",
    duration: "1.08 s",
    requestSize: "186 bytes",
    host: "www.producthunt.com",
    path: "/frontend/graphql",
  },
  {
    id: 86,
    url: "https://www.producthunt.com/frontend/graphql",
    origin: "Google Chrome",
    method: "POST",
    status: "Completed",
    code: 200,
    time: "14:23:29.601",
    duration: "1.69 s",
    requestSize: "320 bytes",
    host: "www.producthunt.com",
    path: "/frontend/graphql",
  },
  {
    id: 87,
    url: "https://www.producthunt.com/frontend/graphql",
    origin: "Google Chrome",
    method: "POST",
    status: "Completed",
    code: 200,
    time: "14:23:29.805",
    duration: "1.28 s",
    requestSize: "2.49 kB",
    host: "www.producthunt.com",
    path: "/frontend/graphql",
  },
  {
    id: 91,
    url: "https://github.githubassets.com/assets/vendors-node_modules_github_selector-observer_dist_index_esm_js-2646a2c533e3.js",
    origin: "Google Chrome",
    method: "GET",
    status: "Completed",
    code: 200,
    time: "14:23:30.150",
    duration: "595 ms",
    requestSize: "7.48 kB",
    host: "github.githubassets.com",
    path: "/assets/vendors-node_modules_github_selector-observer_dist_index_esm_js-2646a2c533e3.js",
  },
  {
    id: 92,
    url: "https://github.githubassets.com/assets/vendors-node_modules_github_relative-time-element_dist_index_js-99e288659d4f.js",
    origin: "Google Chrome",
    method: "GET",
    status: "Completed",
    code: 200,
    time: "14:23:30.350",
    duration: "645 ms",
    requestSize: "8.12 kB",
    host: "github.githubassets.com",
    path: "/assets/vendors-node_modules_github_relative-time-element_dist_index_js-99e288659d4f.js",
  },
  {
    id: 93,
    url: "https://github.githubassets.com/assets/vendors-node_modules_github_text-expander-element_dist_index_js-47db5058e8d7.js",
    origin: "Google Chrome",
    method: "GET",
    status: "Completed",
    code: 200,
    time: "14:23:30.550",
    duration: "712 ms",
    requestSize: "5.89 kB",
    host: "github.githubassets.com",
    path: "/assets/vendors-node_modules_github_text-expander-element_dist_index_js-47db5058e8d7.js",
  },
  {
    id: 94,
    url: "https://github.githubassets.com/assets/vendors-node_modules_github_auto-complete-element_dist_index_js-8b61c6b2942d.js",
    origin: "Google Chrome",
    method: "GET",
    status: "Completed",
    code: 200,
    time: "14:23:30.750",
    duration: "689 ms",
    requestSize: "6.32 kB",
    host: "github.githubassets.com",
    path: "/assets/vendors-node_modules_github_auto-complete-element_dist_index_js-8b61c6b2942d.js",
  },
  {
    id: 98,
    url: "https://www.producthunt.com/frontend/graphql",
    origin: "Google Chrome",
    method: "POST",
    status: "Completed",
    code: 200,
    time: "14:23:30.815",
    duration: "834 ms",
    requestSize: "402 bytes",
    host: "www.producthunt.com",
    path: "/frontend/graphql",
  },
];

export function App() {
  const [selectedRequest, setSelectedRequest] = useState(mockFlows[0]);
  const showEventLog = useSelector(
    (state: RootState) => state.eventLog.visible,
  );
  const showCommandBar = useSelector(
    (state: RootState) => state.commandBar.visible,
  );
  const dispatch = useDispatch();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      dispatch(onKeyDown(e));
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [dispatch]);

  console.log({ showEventLog, showCommandBar }); // TODO: implement these features

  return (
    <div className="font-inter bg-background text-foreground dark: flex h-screen flex-col">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <div className="bg-muted/20 relative w-64 border-r">
          <div className="p-3">
            <SideMenu />
          </div>

          <div className="border-border bg-muted/20 absolute right-0 bottom-0 left-0 border-t p-3">
            <ThemeToggle />
          </div>
        </div>

        <div className="flex-1">
          <FilterPanel />

          <ResizablePanelGroup direction="vertical">
            <ResizablePanel defaultSize={60}>
              <div className="flex h-full flex-col">
                <div className="flex-1 overflow-hidden">
                  <div className="h-full overflow-auto text-xs">
                    <FlowTable
                      flows={mockFlows}
                      selectedRequest={selectedRequest}
                      setSelectedRequest={setSelectedRequest}
                    />
                  </div>
                </div>
              </div>
            </ResizablePanel>

            <ResizableHandle />

            <ResizablePanel defaultSize={40}>
              <div className="bg-muted/30 border-b px-4 py-3">
                <div className="flex items-center gap-3">
                  <Badge
                    variant="outline"
                    className="px-2 py-1 text-sm font-medium"
                  >
                    {selectedRequest.method}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="bg-green-100 px-2 py-1 text-sm text-green-700 dark:bg-green-900/50 dark:text-green-300"
                  >
                    {selectedRequest.code} OK
                  </Badge>
                  <span className="font-mono text-sm text-blue-600 dark:text-blue-400">
                    {selectedRequest.url}
                  </span>
                </div>
              </div>

              <ResizablePanelGroup direction="horizontal">
                <ResizablePanel defaultSize={50}>
                  <RequestDetails />
                </ResizablePanel>

                <ResizableHandle withHandle />

                <ResizablePanel defaultSize={50}>
                  <ResponseDetails />
                </ResizablePanel>
              </ResizablePanelGroup>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>

      <Footer />
    </div>
  );
}
