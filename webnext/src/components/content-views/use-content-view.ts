import {
  useContentView as internalUseContentView,
  type ContentViewData,
} from "web/components/contentviews/useContentView";

export type UserContentViewOptions = Parameters<typeof internalUseContentView>;

export function useContentView(...options: UserContentViewOptions) {
  const contentView = internalUseContentView(...options);

  // Don't render excluded content views.
  if (contentView && isExcludedContentView(contentView.view_name)) {
    return {
      ...contentView,
      text: "",
    } satisfies ContentViewData;
  }

  return contentView;
}

function isExcludedContentView(view: string) {
  // We don't want to include query parameters in body content views because we already have a dedicated query view.
  return view.toLowerCase() === "query";
}
