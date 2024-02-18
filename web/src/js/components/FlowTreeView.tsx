import * as React from "react";
import { useDispatch, useSelector } from "react-redux";
import { useAppSelector } from "../ducks";
import { RequestUtils } from "../flow/utils";
import classnames from "classnames";
import { select } from "../ducks/flows";
import Filt from "../filt/filt";
import { Flow } from "../flow";

interface TreeViewFlowWrapper {
    path: string;
    child: Map<string, TreeViewFlowWrapper>;
    flow: Flow | null;
    highlight: boolean | undefined;
}

interface FlowRowProps {
    active?: boolean;
    flowTree: TreeViewFlowWrapper;
    text: string;
}

function FlowTreeView() {
    const flows = useAppSelector((state) => state.flows.view);
    const newFlows: Map<string, TreeViewFlowWrapper> = new Map(); //we group the flows by host
    const highlightFilter = useAppSelector((state) => state.flows.highlight);
    const isHighlightedFn = highlightFilter
        ? Filt.parse(highlightFilter)
        : () => false;

    //create tree
    flows.map((flow) => {
        if (flow.server_conn?.address) {
            if (flow.type === "http") {
                try {
                    const url = new URL(RequestUtils.pretty_url(flow.request));
                    // if the host hasn't been inserted yet
                    if (!newFlows.has(url.host)) {
                        newFlows.set(url.host, {
                            path: url.href,
                            child: new Map(),
                            flow: null,
                            highlight: false,
                        });
                    }
                    const isHighlighted = flow && isHighlightedFn(flow);
                    //add the flow to the respective host
                    newFlows.get(url.host)?.child.set(url.pathname, {
                        path: url.href,
                        child: new Map(),
                        flow: flow,
                        highlight: isHighlighted,
                    });
                    if (isHighlighted) newFlows.get(url.host)!.highlight = true;
                } catch (error) {
                    console.error(error);
                }
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
                {Array.from(newFlows).map((el, index) => (
                    <FlowRow
                        key={el[0] + "-" + index}
                        flowTree={el[1]}
                        text={el[0]}
                    />
                ))}
            </ul>
        </div>
    );
}

function FlowRow({ active, flowTree, text }: FlowRowProps) {
    const [show, setShow] = React.useState(false);
    const children = Array.from(flowTree.child ?? []);
    const dispatch = useDispatch();
    const selected = useAppSelector((state) => state.flows.selected);

    return (
        <>
            <li
                onClick={() => {
                    if (children.length !== 0) setShow(!show);
                    if (flowTree.flow) dispatch(select(flowTree.flow.id));
                }}
                style={{
                    backgroundColor: active
                        ? "#7bbefc"
                        : flowTree.highlight
                        ? "#ffeb99"
                        : "",
                    cursor: "pointer",
                }}
                className={classnames([
                    "list-group-item",
                    active ? "active" : "",
                ])}
            >
                <span>{text}</span>
            </li>
            <div style={{ display: show ? "block" : "none" }}>
                <pre>
                    {children.map((el, index) => (
                        <FlowRow
                            key={el[0] + "-" + index}
                            flowTree={el[1]}
                            text={el[1].path}
                            active={selected.includes(el[1].flow?.id ?? "")}
                        />
                    ))}
                </pre>
            </div>
        </>
    );
}

export default FlowTreeView;
