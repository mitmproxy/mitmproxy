import React from "react";
import Icon from "../common/Icon";

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
                        <Icon name="expandMore" /> Show more
                    </button>
                ) : (
                    <div key={i}>{line}</div>
                ),
            )}
        </pre>
    );
});
export default ContentRenderer;
