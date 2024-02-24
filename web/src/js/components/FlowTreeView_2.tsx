import * as React from "react";
import { Flow } from "../flow";
import { RequestUtils } from "../flow/utils";

interface TreeElement {
    address: string;
    flow: Flow | null;
    children: TreeElement[];
    highlight?: boolean; //TODO
}

interface FlowTreeView_2Props {
    flows: Flow[];
}

function FlowTreeView_2({ flows }: FlowTreeView_2Props) {
    function buildTree(flows: Flow[]): TreeElement[] {
        const flowsTree: TreeElement = {
            //sort of dummy node, then we return the children of it
            address: "",
            flow: null,
            children: [],
        };

        flows.forEach((flow) => {
            console.log(flow.id);
            if (flow.server_conn?.address && flow.type === "http") {
                const url = new URL(RequestUtils.pretty_url(flow.request));
                const address = url.href;

                const path = address.match(/\/[^\/]+/g);

                let current = flowsTree;

                path?.forEach((_, index) => {
                    const currPath = path.slice(0, index + 1).join("");
                    const child = current.children.find(
                        (e) => e.address === currPath
                    );

                    if (child) {
                        current = child;
                    } else {
                        current.children.push({
                            address: currPath,
                            flow: index === path.length - 1 ? flow : null,
                            children: [],
                        });
                        current = current.children[current.children.length - 1];
                    }
                });
            }
        });

        return flowsTree.children;
    }

    React.useEffect(() => {
        const tree = buildTree(flows);
        console.log(tree);
    }, [flows]);

    return <div>ciao</div>;
}

export default FlowTreeView_2;
