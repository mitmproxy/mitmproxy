import * as React from "react";
import { Flow } from "../flow";
import { RequestUtils } from "../flow/utils";
import classnames from "classnames";
import Filt from "../filt/filt";
import { select } from "../ducks/flows";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../ducks";

interface TreeElement {
    address: string;
    flow: Flow | null;
    children: TreeElement[];
    hidden?: boolean;
    isHighlighted?: boolean;
    active?: boolean;
}

interface FlowTreeViewProps {
    flows: Flow[];
    highlight?: string;
}

interface FlowRowProps {
    treeElement: TreeElement;
    toggleNode: (treeElement: TreeElement) => void;
    active?: boolean;
}

function FlowTreeView({ flows, highlight }: FlowTreeViewProps) {
    const [treeView, setTreeView] = React.useState<TreeElement[]>([]);

    //to manage the highlighting of a group (row)
    const isHighlightedFn = highlight ? Filt.parse(highlight) : () => false;

    const selected = useAppSelector((state) => state.flows.selected);

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
                const protocol = url.protocol;
                const path = address.match(/\/[^\/]+/g);

                let current = flowsTree;

                path?.forEach((_, index) => {
                    const currPath = path.slice(0, index + 1).join("");

                    const currPathComplete = protocol + "/" + currPath;

                    const child = current.children.find(
                        (e) => e.address === currPathComplete
                    );

                    if (child) {
                        current = child;
                    } else {
                        current.children.push({
                            address: currPathComplete,
                            flow: index === path.length - 1 ? flow : null,
                            children: [],
                            hidden: true,
                            isHighlighted: flow && isHighlightedFn(flow),
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
    }, [flows, highlight]);

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
                        active={selected.includes(element.flow?.id ?? "")}
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

function FlowRow({ treeElement, toggleNode, active }: FlowRowProps) {
    const rotateSymbolRef = React.useRef<HTMLElement>(null);

    const handleToggle = (
        event: React.MouseEvent<HTMLLIElement, MouseEvent>
    ) => {
        event.preventDefault();
        toggleNode(treeElement);
        rotateSymbol(rotateSymbolRef.current);
    };

    const dispatch = useDispatch();
    const selected = useAppSelector((state) => state.flows.selected);

    return (
        <>
            <li
                onClick={() => {
                    if (treeElement.flow) dispatch(select(treeElement.flow.id));
                }}
                onDoubleClick={handleToggle}
                className={classnames("list-group-item", {
                    "has-children": treeElement.children.length > 0,
                })}
                style={{
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "row",
                    gap: treeElement.children.length > 0 ? 15 : 25,
                    marginBottom: 10,
                    backgroundColor: active
                        ? "#7bbefc"
                        : treeElement.isHighlighted
                        ? "#ffeb99"
                        : treeElement.children.length > 0
                        ? "#f5f5f5"
                        : "",
                    userSelect: "none",
                }}
            >
                <span
                    ref={rotateSymbolRef}
                    className="rotate-symbol"
                    onClick={handleToggle}
                >
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
                            active={selected.includes(element.flow?.id ?? "")}
                        />
                    )}
                </div>
            ))}
        </>
    );
}

export default FlowTreeView;
