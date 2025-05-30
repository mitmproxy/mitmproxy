import { Activity, Settings, Wifi, ArrowRight, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function CaptureSetup() {
  return (
    <div className="bg-background mx-auto flex items-center justify-center p-4">
      <div className="w-full max-w-2xl space-y-8 text-center">
        <div className="mb-8 flex items-center justify-center gap-3">
          <div className="bg-accent text-accent-foreground flex items-center gap-2 rounded-full border px-4 py-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-green-500"></div>
            <span className="font-medium">mitmproxy is running</span>
          </div>
        </div>

        <div className="relative">
          <div className="bg-muted mx-auto mb-6 flex h-32 w-32 items-center justify-center rounded-full border">
            <Activity className="text-primary h-16 w-16" strokeWidth={1.5} />
          </div>

          <div className="bg-secondary absolute top-4 left-1/4 flex h-8 w-8 items-center justify-center rounded-full border">
            <Wifi className="text-secondary-foreground h-4 w-4" />
          </div>
          <div className="bg-accent absolute top-8 right-1/4 flex h-6 w-6 items-center justify-center rounded-full border">
            <Settings className="text-accent-foreground h-3 w-3" />
          </div>
        </div>

        <div className="space-y-4">
          <h1 className="text-foreground text-3xl font-bold">
            Ready to capture traffic
          </h1>
          <p className="text-muted-foreground mx-auto max-w-md text-lg">
            No network flows have been recorded yet. Configure your capture
            settings to start monitoring HTTP/HTTPS traffic.
          </p>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Card className="border-border hover:border-primary/50 group border-2 border-dashed transition-colors">
            <CardContent className="p-6 text-center">
              <div className="bg-primary/10 group-hover:bg-primary/20 mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg transition-colors">
                <Settings className="text-primary h-6 w-6" />
              </div>
              <h3 className="text-foreground mb-2 font-semibold">
                Configure Capture
              </h3>
              <p className="text-muted-foreground mb-4 text-sm">
                Set up your proxy settings and filters to start capturing
                traffic
              </p>
              <Button variant="outline" className="w-full">
                Open Capture Tab
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>

          <Card className="border-border hover:border-primary/50 group border-2 border-dashed transition-colors">
            <CardContent className="p-6 text-center">
              <div className="bg-primary/10 group-hover:bg-primary/20 mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg transition-colors">
                <Play className="text-primary h-6 w-6" />
              </div>
              <h3 className="text-foreground mb-2 font-semibold">
                Quick Start
              </h3>
              <p className="text-muted-foreground mb-4 text-sm">
                Follow our setup guide to get started with traffic interception
              </p>
              <Button variant="outline" className="w-full">
                View Guide
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="bg-muted mt-8 rounded-lg border p-6">
          <h4 className="text-foreground mb-2 font-medium">
            Need help getting started?
          </h4>
          <p className="text-muted-foreground mb-8 text-sm">
            Make sure your device is configured to use mitmproxy as its HTTP
            proxy. The default proxy address is{" "}
            <code className="bg-secondary text-secondary-foreground rounded px-2 py-1 text-xs">
              localhost:8080
            </code>
          </p>
          <div className="flex flex-wrap justify-center gap-8 text-sm">
            <a href="#" className="hover:underline">
              Documentation
            </a>
            <a href="#" className="hover:underline">
              Troubleshooting
            </a>
            <a href="#" className="hover:underline">
              Examples
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
