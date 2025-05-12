import * as React from "react";
import Button from "../common/Button";
import {
    canReplay,
    canResumeOrKill,
    canRevert,
    MessageUtils,
} from "../../flow/utils";
import HideInStatic from "../common/HideInStatic";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    duplicate as duplicateFlows,
    kill as killFlows,
    remove as removeFlows,
    replay as replayFlows,
    resume as resumeFlows,
    revert as revertFlows,
    mark as markFlows,
} from "../../ducks/flows";
import Dropdown, { MenuItem } from "../common/Dropdown";
import { copy } from "../../flow/export";
import { Flow } from "../../flow";

import type { JSX } from "react";

FlowMenu.title = "Flow";

export default function FlowMenu(): JSX.Element {
    const dispatch = useAppDispatch();

    const selectedFlows = useAppSelector((state) => state.flows.selected);
    const flow = selectedFlows[0];

    const canResumeOrKillAny = selectedFlows.some(canResumeOrKill);

    if (selectedFlows.length === 0) return <div />;
    return (
        <div className="flow-menu">
            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <Button
                            title="[r]eplay flow"
                            icon="fa-repeat text-primary"
                            onClick={() => dispatch(replayFlows(selectedFlows))}
                            disabled={!selectedFlows.some(canReplay)}
                        >
                            Replay
                        </Button>
                        <Button
                            title="[D]uplicate flow"
                            icon="fa-copy text-info"
                            onClick={() =>
                                dispatch(duplicateFlows(selectedFlows))
                            }
                        >
                            Duplicate
                        </Button>
                        <Button
                            disabled={!selectedFlows.some(canRevert)}
                            title="revert changes to flow [V]"
                            icon="fa-history text-warning"
                            onClick={() => dispatch(revertFlows(selectedFlows))}
                        >
                            Revert
                        </Button>
                        <Button
                            title="[d]elete flow"
                            icon="fa-trash text-danger"
                            onClick={() => {
                                dispatch(removeFlows(selectedFlows));
                            }}
                        >
                            Delete
                        </Button>

                        <MarkButton flows={selectedFlows} />
                    </div>
                    <div className="menu-legend">Flow Modification</div>
                </div>
            </HideInStatic>

            <div className="menu-group">
                <div className="menu-content">
                    <DownloadButton flow={flow} />
                    <ExportButton flow={flow} />
                </div>
                <div className="menu-legend">Export</div>
            </div>

            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <Button
                            disabled={!canResumeOrKillAny}
                            title="[a]ccept intercepted flow"
                            icon="fa-play text-success"
                            onClick={() => dispatch(resumeFlows(selectedFlows))}
                        >
                            Resume
                        </Button>
                        <Button
                            disabled={!canResumeOrKillAny}
                            title="kill intercepted flow [x]"
                            icon="fa-times text-danger"
                            onClick={() => dispatch(killFlows(selectedFlows))}
                        >
                            Abort
                        </Button>
                    </div>
                    <div className="menu-legend">Interception</div>
                </div>
            </HideInStatic>
        </div>
    );
}

// Reference: https://stackoverflow.com/a/63627688/9921431
const openInNewTab = (url) => {
    const newWindow = window.open(url, "_blank", "noopener,noreferrer");
    if (newWindow) newWindow.opener = null;
};

function DownloadButton({ flow }: { flow: Flow }) {
    const hasSingleFlowSelected = useAppSelector(
        (state) => state.flows.selected.length === 1,
    );

    if (flow.type !== "http")
        return (
            <Button icon="fa-download" onClick={() => 0} disabled>
                Download
            </Button>
        );

    if (flow.request.contentLength && !flow.response?.contentLength) {
        return (
            <Button
                icon="fa-download"
                onClick={() =>
                    openInNewTab(MessageUtils.getContentURL(flow, flow.request))
                }
                disabled={!hasSingleFlowSelected}
            >
                Download
            </Button>
        );
    }
    if (flow.response) {
        const response = flow.response;
        if (!flow.request.contentLength && flow.response.contentLength) {
            return (
                <Button
                    icon="fa-download"
                    onClick={() =>
                        openInNewTab(MessageUtils.getContentURL(flow, response))
                    }
                    disabled={!hasSingleFlowSelected}
                >
                    Download
                </Button>
            );
        }
        if (flow.request.contentLength && flow.response.contentLength) {
            return (
                <Dropdown
                    text={
                        <Button
                            icon="fa-download"
                            onClick={() => 1}
                            disabled={!hasSingleFlowSelected}
                        >
                            Download▾
                        </Button>
                    }
                    options={{ placement: "bottom-start" }}
                >
                    <MenuItem
                        onClick={() =>
                            openInNewTab(
                                MessageUtils.getContentURL(flow, flow.request),
                            )
                        }
                    >
                        Download request
                    </MenuItem>
                    <MenuItem
                        onClick={() =>
                            openInNewTab(
                                MessageUtils.getContentURL(flow, response),
                            )
                        }
                    >
                        Download response
                    </MenuItem>
                </Dropdown>
            );
        }
    }

    return null;
}

function ExportButton({ flow }: { flow: Flow }) {
    const hasSingleFlowSelected = useAppSelector(
        (state) => state.flows.selected.length === 1,
    );
    return (
        <Dropdown
            className=""
            text={
                <Button
                    title="Export flow."
                    icon="fa-clone"
                    onClick={() => 1}
                    disabled={flow.type !== "http" || !hasSingleFlowSelected}
                >
                    Export▾
                </Button>
            }
            options={{ placement: "bottom-start" }}
        >
            <MenuItem onClick={() => copy(flow, "raw_request")}>
                Copy raw request
            </MenuItem>
            <MenuItem onClick={() => copy(flow, "raw_response")}>
                Copy raw response
            </MenuItem>
            <MenuItem onClick={() => copy(flow, "raw")}>
                Copy raw request and response
            </MenuItem>
            <MenuItem onClick={() => copy(flow, "curl")}>Copy as cURL</MenuItem>
            <MenuItem onClick={() => copy(flow, "httpie")}>
                Copy as HTTPie
            </MenuItem>
        </Dropdown>
    );
}

const markers = {
    ":red_circle:": "🔴",
    ":orange_circle:": "🟠",
    ":yellow_circle:": "🟡",
    ":green_circle:": "🟢",
    ":large_blue_circle:": "🔵",
    ":purple_circle:": "🟣",
    ":brown_circle:": "🟤",
};

function MarkButton({ flows }: { flows: Flow[] }) {
    const dispatch = useAppDispatch();
    return (
        <Dropdown
            className=""
            text={
                <Button
                    title="mark flow"
                    icon="fa-paint-brush text-success"
                    onClick={() => 1}
                >
                    Mark▾
                </Button>
            }
            options={{ placement: "bottom-start" }}
        >
            <MenuItem onClick={() => dispatch(markFlows(flows, ""))}>
                ⚪ (no marker)
            </MenuItem>
            {Object.entries(markers).map(([name, sym]) => (
                <MenuItem
                    key={name}
                    onClick={() => dispatch(markFlows(flows, name))}
                >
                    {sym} {name.replace(/[:_]/g, " ")}
                </MenuItem>
            ))}
        </Dropdown>
    );
}
