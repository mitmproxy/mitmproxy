import { Flow } from "../../flow";
import * as React from "react";
import ValueEditor from "../editors/ValueEditor";
import { useAppDispatch } from "../../ducks";
import * as flowActions from "../../ducks/flows";

export default function Comment({ flow }: { flow: Flow }) {
    const dispatch = useAppDispatch();

    return (
        <section className="timing">
            <h4>Comment</h4>
            <ValueEditor
                className="kv-value"
                content={flow.comment}
                onEditDone={(comment) => {
                    dispatch(flowActions.update(flow, { comment }));
                }}
                placeholder="empty"
                selectAllOnClick={true}
            />
        </section>
    );
}
Comment.displayName = "Comment";
