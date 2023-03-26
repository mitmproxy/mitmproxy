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
    flow: Flow | null,
    highlight: boolean | undefined
}

function FlowTreeView() {
    const flows = useAppSelector((state) => state.flows.list);
    const newFlows: Map<string, TreeViewFlowWrapper> = new Map();
    const highlightFilter = useAppSelector((state) => state.flows.highlight);
    const isHighlightedFn = highlightFilter ? Filt.parse(highlightFilter) : () => false;

    flows.map((flow) => {
        if (flow.server_conn?.address) {
            if (flow.type === "http") {
                try {
                    const url = new URL(RequestUtils.pretty_url(flow.request));
                    if (!newFlows.has(url.host)) {
                        newFlows.set(url.host, {
                            path: url.href,
                            child: new Map(),
                            flow: null,
                            highlight: false
                        });
                    }
                    const isHighlighted = flow && isHighlightedFn(flow)
                    newFlows.get(url.host)?.child.set(url.pathname, {
                        path: url.href,
                        child: new Map(),
                        flow: flow,
                        highlight: isHighlighted
                    });
                    if (isHighlighted) newFlows.get(url.host)!.highlight = true
                } catch (error) {
                    console.error(error);
                }
            }
        }
    });

    return (
        <div className="flow-table" style={{
            width: "100%", maxHeight: "90vh"
        }}>
            <ul className="list-group w-100 overflow-auto" style={{ width: "100%", height: "100%" }
            } >
                {
                    Array.from(newFlows).map((el) => (
                        <FlowRow flow={el[1]} text={el[0]} />
                    ))
                }
            </ ul>
        </div>
    );
}

function FlowRow({
    active,
    flow,
    text,
}: {
    active?: boolean;
    show?: boolean;
    flow: TreeViewFlowWrapper;
    text: string;
}) {
    const [show, setShow] = React.useState(false);
    const childs = Array.from(flow.child ?? []);
    const dispatch = useDispatch()

    return (
        <>
            <li
                onClick={() => {
                    if (childs.length !== 0) setShow(!show)
                    if (flow.flow) dispatch(select(flow.flow.id));
                }}
                style={{ backgroundColor: flow.highlight ? "aqua" : "" }}
                className={classnames(["list-group-item", active ? "active" : ""])}
            >
                <span style={{}}>

                </span>
                {text}
            </li>
            <div style={{ display: show ? "block" : "none" }}>
                <pre>
                    {childs.map((el) => (
                        <FlowRow flow={el[1]} text={el[1].path} />
                    ))}
                </pre>
            </div>
        </>
    );
}


export default FlowTreeView;
