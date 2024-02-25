import * as React from "react";
import { Flow } from "../flow";
import { RequestUtils } from "../flow/utils";
import classnames from "classnames";

interface TreeElement {
    address: string;
    flow: Flow | null;
    children: TreeElement[];
    hidden?: boolean;
}

interface FlowTreeViewProps {
    flows: Flow[];
}

interface FlowRowProps {
    treeElement: TreeElement;
    toggleNode: (treeElement: TreeElement) => void;
}

function FlowTreeView({ flows }: FlowTreeViewProps) {
    const [treeView, setTreeView] = React.useState<TreeElement[]>([]);

    function buildTree(flows: Flow[]): TreeElement[] {
        const flowsTree: TreeElement = {
            address: "",
            flow: null,
            children: [],
        };

        flows.forEach((flow) => {
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
                            hidden: true,
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
        setTreeView(tree);
    }, [flows]);

    const toggleNode = (treeElement: TreeElement) => {
        treeElement.children.forEach((child) => {
            child.hidden = !child.hidden;
            child.children.forEach((c) => {
                c.hidden = true;
            });
        });
        setTreeView([...treeView]);
    };

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
                {treeView.map((element, index) => (
                    <FlowRow
                        key={index}
                        treeElement={element}
                        toggleNode={toggleNode}
                    />
                ))}
            </ul>
        </div>
    );
}

function rotateSymbol(symbol: HTMLElement | null) {
    if (symbol) {
        if (symbol.style.transform === "rotate(180deg)") {
            symbol.style.transform = "rotate(90deg)";
        } else {
            symbol.style.transform = "rotate(180deg)";
        }
    }
}

function FlowRow({ treeElement, toggleNode }: FlowRowProps) {
    const rotateSymbolRef = React.useRef<HTMLElement>(null);

    const handleToggle = () => {
        toggleNode(treeElement);
        rotateSymbol(rotateSymbolRef.current);
    };

    return (
        <>
            <li
                onClick={handleToggle}
                className={classnames("list-group-item", {
                    "has-children": treeElement.children.length > 0,
                })}
                style={{
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "row",
                    gap: 15,
                    marginBottom: 10,
                }}
            >
                <span ref={rotateSymbolRef} className="rotate-symbol">
                    {treeElement.children.length > 0 ? "^" : ""}
                </span>
                <span>{treeElement.address}</span>
            </li>
            {treeElement.children.map((element, index) => (
                <div key={index} style={{ paddingLeft: 30 }}>
                    {!element.hidden && (
                        <FlowRow
                            treeElement={element}
                            toggleNode={toggleNode}
                        />
                    )}
                </div>
            ))}
        </>
    );
}

export default FlowTreeView;
