import * as React from "react";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../ducks";
import { RequestUtils } from "../flow/utils";
import classnames from "classnames";
import Filt from "../filt/filt";
import { Flow } from "../flow";
import FlowTable from "./FlowTable";

interface TreeView {
    host: string;
    flows: Flow[];
    highlight?: boolean;
    active?: boolean;
}

function FlowTreeView({
    flows,
    highlight,
}: {
    flows: Flow[];
    highlight?: string;
}) {
    const treeViewFlows: TreeView[] = []; //we group the flows by host
    const isHighlightedFn = highlight ? Filt.parse(highlight) : () => false;

    //create the tree
    flows.map((flow) => {
        if (flow.server_conn?.address && flow.type === "http") {
            try {
                const url = new URL(RequestUtils.pretty_url(flow.request));

                //check for the index
                const existingIndex = treeViewFlows.findIndex(
                    (item) => item.host === url.host
                );

                if (existingIndex !== -1) {
                    // If host already exists, append the flow
                    treeViewFlows[existingIndex].flows.push(flow);
                    treeViewFlows[existingIndex].highlight =
                        flow && isHighlightedFn(flow);
                } else {
                    // If host doesn't exist, add the entire object
                    treeViewFlows.push({
                        host: url.host,
                        flows: [flow],
                        highlight: flow && isHighlightedFn(flow),
                    });
                }
            } catch (error) {
                console.error(error);
            }
        }
    });

    return (
        <div
            className="flow-table"
            style={{
                width: "100%",
                maxHeight: "90vh",
            }}
        >
            <ul
                className="list-group w-100 overflow-auto"
                style={{ width: "100%", height: "100%" }}
            >
                {treeViewFlows.map((el, index) => (
                    <FlowRow
                        key={el.host + "-" + index}
                        flows={el.flows}
                        host={el.host}
                    />
                ))}
            </ul>
        </div>
    );
}

function FlowRow({ active, host, highlight, flows }: TreeView) {
    const [show, setShow] = React.useState(false);

    const dispatch = useDispatch();
    const selected = useAppSelector((state) => state.flows.selected);

    React.useEffect(() => console.log(flows));

    return (
        <>
            <li
                onClick={() => {
                    if (flows.length !== 0) setShow(!show);
                    //if (flowTree.flow) dispatch(select(flowTree.flow.id));
                }}
                style={{
                    backgroundColor: active
                        ? "#7bbefc"
                        : highlight
                        ? "#ffeb99"
                        : "",
                    cursor: "pointer",
                }}
                className={classnames([
                    "list-group-item",
                    active ? "active" : "",
                ])}
            >
                <span>{host}</span>
            </li>
            {show && (
                <div style={{ padding: 10, backgroundColor: "lightgray" }}>
                    <FlowTable
                        flows={flows}
                        highlight={highlight}
                        selected={selected}
                    />
                </div>
            )}
        </>
    );
}

export default FlowTreeView;
