import React from "react";

type ContentRendererProps = {
    content: string;
    maxLines: number;
    showMore: () => void;
};

const ContentRenderer = React.memo(function ContentRenderer({
    content,
    maxLines,
    showMore,
}: ContentRendererProps) {
    if (content.length === 0) {
        return null;
    }
    return (
        <pre>
            {content.split("\n").map((line, i) =>
                i === maxLines ? (
                    <button
                        key="showmore"
                        onClick={showMore}
                        className="btn btn-xs btn-info"
                    >
                        <i
                            className="fa fa-angle-double-down"
                            aria-hidden="true"
                        />{" "}
                        Show more
                    </button>
                ) : (
                    <div key={i}>{line}</div>
                ),
            )}
        </pre>
    );
});
export default ContentRenderer;
