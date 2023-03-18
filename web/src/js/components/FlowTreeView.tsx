import * as React from "react";
import { useSelector } from "react-redux";
import { useAppSelector } from "../ducks";
import { RequestUtils } from "../flow/utils";

interface TreeViewFlow {
    path: string;
    child: Map<string, TreeViewFlow>;
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
                        });
                    newFlows.get(url.host)?.child.set(url.pathname, {
                        path: url.href,
                        child: new Map(),
                    });
                } catch (error) {
                    console.error(error);
                }
            }
        }
    });

    return (
        <ul className="list-group w-100" style={{ width: "100%" }}>
            {Array.from(newFlows).map((el) => (
                <FlowRow flow={el[1]} text={el[0]} />
            ))}
        </ul>
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
    return (
        <>
            <li
                onClick={() => setShow(!show)}
                className={`list-group-item ${active ? "active" : ""}`}
                data-bs-toggle="collapse"
            >
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
