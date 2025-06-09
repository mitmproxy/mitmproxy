import { useState } from "react";
import { useAppDispatch, useAppSelector } from "web/ducks/hooks";
import type { HTTPFlow, HTTPMessage } from "web/flow";
import { ContentRenderer } from "./content-renderer";
import { CONTENT_VIEW_ALL_LINES, useContentView } from "./use-content-view";
import { ContentViewSelector } from "@/components/content-views/content-view-selector";
import { setContentViewFor } from "web/ducks/ui/flow";

export type HttpMessageContentViewProps = {
  flow: HTTPFlow;
  message: HTTPMessage;
};

export function HttpMessageContentView({
  flow,
  message,
}: HttpMessageContentViewProps) {
  const part = flow.request === message ? "request" : "response";
  const dispatch = useAppDispatch();

  const contentView = useAppSelector(
    (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
  );
  const [maxLines, setMaxLines] = useState<number>(
    useAppSelector((state) => state.options.content_view_lines_cutoff),
  );
  const showMore = () => setMaxLines((value) => Math.max(1024, value * 2));
  const showAll = () => setMaxLines(CONTENT_VIEW_ALL_LINES);
  const contentViewData = useContentView(
    flow,
    message,
    contentView,
    maxLines + 1,
    message.contentHash,
  );
  const selectContentView = (value: string) => {
    dispatch(
      setContentViewFor({
        messageId: flow.id + part,
        contentView: value,
      }),
    );
  };

  const contentType = message?.headers?.find(
    ([header]) => header.toLowerCase() === "content-type",
  )?.[1];

  return (
    <div className="h-full">
      {contentViewData === undefined && (
        <p className="text-muted-foreground text-xs">Loading...</p>
      )}

      {contentViewData && contentViewData.text.length == 0 && (
        <p className="text-muted-foreground text-xs">No data</p>
      )}

      {contentViewData && contentViewData.text.length > 0 && (
        <ContentRenderer
          content={contentViewData.text}
          contentViewName={contentViewData.view_name}
          contentType={contentType}
          maxLines={maxLines}
          part={part}
          showMore={showMore}
          showAll={showAll}
        >
          <ContentViewSelector
            value={contentView}
            contentType={contentType}
            onChange={selectContentView}
          />
        </ContentRenderer>
      )}
    </div>
  );
}
