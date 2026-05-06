import React from "react";
import { useTranslation } from "react-i18next";

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
    const { t } = useTranslation();
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
                        {t("contentview.showMore")}
                    </button>
                ) : (
                    <div key={i}>{line}</div>
                ),
            )}
        </pre>
    );
});
export default ContentRenderer;
