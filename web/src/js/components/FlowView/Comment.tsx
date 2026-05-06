import type { Flow } from "../../flow";
import * as React from "react";
import { useTranslation } from "react-i18next";
import ValueEditor from "../editors/ValueEditor";
import { useAppDispatch } from "../../ducks";
import * as flowActions from "../../ducks/flows";

export default function Comment({ flow }: { flow: Flow }) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    return (
        <section className="timing">
            <h4>{t("flowView.comment.title")}</h4>
            <ValueEditor
                className="kv-value"
                content={flow.comment}
                onEditDone={(comment) => {
                    dispatch(flowActions.update(flow, { comment }));
                }}
                placeholder={t("flowView.comment.placeholder")}
                selectAllOnClick={true}
            />
        </section>
    );
}
Comment.displayName = "Comment";
