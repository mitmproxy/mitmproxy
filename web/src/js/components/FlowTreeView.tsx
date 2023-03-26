import * as React from "react";
import { useDispatch, useSelector } from "react-redux";
import { useAppSelector } from "../ducks";
import { RequestUtils } from "../flow/utils";
import classnames from "classnames";
import { select } from "../ducks/flows";

interface TreeViewFlow {
    path: string;
    child: Map<string, TreeViewFlow>;
    flow_id: string | null
}

function FlowTreeView() {
    const flows = useAppSelector((state) => state.flows.list);
    const newFlows: Map<string, TreeViewFlow> = new Map();

    flows.map((flow) => {
        if (flow.server_conn?.address) {
            if (flow.type === "http") {
                try {
                    const url = new URL(RequestUtils.pretty_url(flow.request));
                    if (!newFlows.has(url.host))
                        newFlows.set(url.host, {
                            path: url.href,
                            child: new Map(),
                            flow_id: null
                        });
                    newFlows.get(url.host)?.child.set(url.pathname, {
                        path: url.href,
                        child: new Map(),
                        flow_id: flow.id
                    });
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
    flow: TreeViewFlow;
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
                    if (flow.flow_id) dispatch(select(flow.flow_id));

                }}
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
