import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  type TabsProps,
} from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useAppSelector } from "web/ducks";
import type { Flow } from "web/flow";

export type TabProps = {
  flow: Flow;
};

export type Tab = {
  name: string;
  value: string;
  component: React.ComponentType<TabProps>;
  scrollable?: boolean;
};

export type PanelTabsProps = {
  title: string;
  tabs: Tab[];
} & TabsProps;

export function PanelTabs({
  tabs,
  title,
  className,
  ...props
}: PanelTabsProps) {
  const flow = useAppSelector((state) => state.flows.selected[0]);

  return (
    <Tabs {...props} className={cn("h-full p-4", className)}>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-sm font-medium">{title}</span>
      </div>
      <TabsList>
        {tabs.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value} className="text-xs">
            {tab.name}
          </TabsTrigger>
        ))}
      </TabsList>

      {tabs.map((tab) => (
        <TabsContent
          key={tab.value}
          value={tab.value}
          className={cn("min-h-0", { "h-full": tab.scrollable })}
        >
          {tab.scrollable ? (
            <ScrollArea className="h-full">
              <tab.component flow={flow} />
            </ScrollArea>
          ) : (
            <tab.component flow={flow} />
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}
