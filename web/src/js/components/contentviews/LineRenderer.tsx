import React from "react";

type ContentLinesRendererProps = {
    lines: [style: string, text: string][][];
    maxLines: number;
    showMore: () => void;
};

const LineRenderer = React.memo(function LineRenderer({
    lines,
    maxLines,
    showMore,
}: ContentLinesRendererProps) {
    if (lines.length === 0) {
        return null;
    }
    return (
        <pre>
            {lines.map((line, i) =>
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
                    <div key={i}>
                        {line.map(([style, text], j) => (
                            <span key={j} className={style}>
                                {text}
                            </span>
                        ))}
                    </div>
                ),
            )}
        </pre>
    );
});
export default LineRenderer;
