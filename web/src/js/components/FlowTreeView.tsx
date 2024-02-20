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
    highlight?: string;
    active?: boolean;
}

function FlowTreeView({
    flows,
    highlight,
}: {
    flows: Flow[];
    highlight?: string;
}) {
    /*
    Note for the SORTING: 
        The idea is that we get the initial order of the hosts and we save it.
        Then, every time the flows order change (due to the sorting) we simply modify the flows of the related host.
    */

    const [initialHosts, setInitialHosts] = React.useState<string[]>([]); //to keep track of the initial hosts (useful when sorting)

    // Initialize the initialHosts when the component mounts
    React.useEffect(() => {
        const hosts = new Set<string>();
        flows.forEach((flow) => {
            if (flow.server_conn?.address && flow.type === "http") {
                const url = new URL(RequestUtils.pretty_url(flow.request));
                hosts.add(url.host);
            }
        });
        setInitialHosts(Array.from(hosts));
    }, []);

    // Group the flows by host
    const groupedFlows = React.useMemo(() => {
        const groups: { [host: string]: Flow[] } = {};

        flows.forEach((flow) => {
            if (flow.server_conn?.address && flow.type === "http") {
                const url = new URL(RequestUtils.pretty_url(flow.request));
                const host = url.host;
                if (!groups[host]) {
                    groups[host] = [];
                }
                groups[host].push(flow);
            }
        });

        return groups;
    }, [flows]);

    return (
        <div
            style={{
                width: "100%",
                maxHeight: "90vh",
            }}
        >
            <ul
                className="list-group w-100 overflow-auto"
                style={{ width: "100%", height: "100%" }}
            >
                {initialHosts.map((host, index) => (
                    <FlowGroup
                        key={host + "-" + index}
                        flows={groupedFlows[host] || []}
                        host={host}
                        highlight={highlight}
                    />
                ))}
            </ul>
        </div>
    );
}

function FlowGroup({ active, host, highlight, flows }: TreeView) {
    const [show, setShow] = React.useState(false);

    const selected = useAppSelector(
        (state) => state.flows.byId[state.flows.selected[0]]
    );

    //to manage the highlighting of a group (row)
    const isHighlighted = highlight ? Filt.parse(highlight) : () => false;
    const isRowHighlighted =
        flows.filter((flow) => isHighlighted(flow)).length > 0;

    return (
        <>
            <li
                onClick={() => {
                    if (flows.length !== 0) setShow(!show);
                }}
                style={{
                    backgroundColor: active
                        ? "#7bbefc"
                        : isRowHighlighted
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
                <div style={{ padding: 10, backgroundColor: "#e0e0e0" }}>
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
