import { useCallback, useState } from "react";
import { useAppSelector } from "web/ducks/hooks";
import type { HTTPFlow } from "web/flow";
import { ContentRenderer, type ContentRendererProps } from "./content-renderer";
import { useContentView } from "./use-content-view";

export type HttpMessageContentViewProps = {
  flow: HTTPFlow;
  part: ContentRendererProps["part"];
};

export function HttpMessageContentView({
  flow,
  part,
}: HttpMessageContentViewProps) {
  const contentView = useAppSelector(
    (state) => state.ui.flow.contentViewFor[flow.id + part] || "Auto",
  );
  const [maxLines, setMaxLines] = useState<number>(
    useAppSelector((state) => state.options.content_view_lines_cutoff),
  );
  const showMore = useCallback(
    () => setMaxLines((value) => Math.max(1024, value * 2)),
    [],
  );
  const contentViewData = useContentView(
    flow,
    part,
    contentView,
    maxLines + 1,
    flow.request.contentHash,
  );
  const contentType = flow.request.headers.find(
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
          contentType={contentType}
          maxLines={maxLines}
          showMore={showMore}
          part={part}
        />
      )}
    </div>
  );
}
