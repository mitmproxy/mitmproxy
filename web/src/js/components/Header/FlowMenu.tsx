import * as React from "react";
import { useTranslation } from "react-i18next";
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
import type { Flow } from "../../flow";

import type { JSX } from "react";

FlowMenu.title = "Flow";

export default function FlowMenu(): JSX.Element {
    const { t } = useTranslation();
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
                            title={t("header.flowMenu.replayTitle")}
                            icon="fa-repeat text-primary"
                            onClick={() => dispatch(replayFlows(selectedFlows))}
                            disabled={!selectedFlows.some(canReplay)}
                        >
                            {t("header.flowMenu.replay")}
                        </Button>
                        <Button
                            title={t("header.flowMenu.duplicateTitle")}
                            icon="fa-copy text-info"
                            onClick={() =>
                                dispatch(duplicateFlows(selectedFlows))
                            }
                        >
                            {t("header.flowMenu.duplicate")}
                        </Button>
                        <Button
                            disabled={!selectedFlows.some(canRevert)}
                            title={t("header.flowMenu.revertTitle")}
                            icon="fa-history text-warning"
                            onClick={() => dispatch(revertFlows(selectedFlows))}
                        >
                            {t("header.flowMenu.revert")}
                        </Button>
                        <Button
                            title={t("header.flowMenu.deleteTitle")}
                            icon="fa-trash text-danger"
                            onClick={() => {
                                dispatch(removeFlows(selectedFlows));
                            }}
                        >
                            {t("header.flowMenu.delete")}
                        </Button>

                        <MarkButton flows={selectedFlows} />
                    </div>
                    <div className="menu-legend">{t("header.flowMenu.flowModification")}</div>
                </div>
            </HideInStatic>

            <div className="menu-group">
                <div className="menu-content">
                    <DownloadButton flow={flow} />
                    <ExportButton flow={flow} />
                </div>
                <div className="menu-legend">{t("header.flowMenu.export")}</div>
            </div>

            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <Button
                            disabled={!canResumeOrKillAny}
                            title={t("header.flowMenu.resumeTitle")}
                            icon="fa-play text-success"
                            onClick={() => dispatch(resumeFlows(selectedFlows))}
                        >
                            {t("header.flowMenu.resume")}
                        </Button>
                        <Button
                            disabled={!canResumeOrKillAny}
                            title={t("header.flowMenu.abortTitle")}
                            icon="fa-times text-danger"
                            onClick={() => dispatch(killFlows(selectedFlows))}
                        >
                            {t("header.flowMenu.abort")}
                        </Button>
                    </div>
                    <div className="menu-legend">{t("header.flowMenu.interception")}</div>
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
    const { t } = useTranslation();
    const hasSingleFlowSelected = useAppSelector(
        (state) => state.flows.selected.length === 1,
    );

    if (flow.type !== "http")
        return (
            <Button icon="fa-download" onClick={() => 0} disabled>
                {t("header.flowMenu.download")}
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
                {t("header.flowMenu.download")}
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
                    {t("header.flowMenu.download")}
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
                            {t("header.flowMenu.download")}▾
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
                        {t("header.flowMenu.downloadRequest")}
                    </MenuItem>
                    <MenuItem
                        onClick={() =>
                            openInNewTab(
                                MessageUtils.getContentURL(flow, response),
                            )
                        }
                    >
                        {t("header.flowMenu.downloadResponse")}
                    </MenuItem>
                </Dropdown>
            );
        }
    }

    return null;
}

function ExportButton({ flow }: { flow: Flow }) {
    const { t } = useTranslation();
    const hasSingleFlowSelected = useAppSelector(
        (state) => state.flows.selected.length === 1,
    );
    return (
        <Dropdown
            className=""
            text={
                <Button
                    title={t("header.flowMenu.exportTooltip")}
                    icon="fa-clone"
                    onClick={() => 1}
                    disabled={flow.type !== "http" || !hasSingleFlowSelected}
                >
                    {t("header.flowMenu.export")}▾
                </Button>
            }
            options={{ placement: "bottom-start" }}
        >
            <MenuItem onClick={() => copy(flow, "raw_request")}>
                {t("header.flowMenu.copyRawRequest")}
            </MenuItem>
            <MenuItem onClick={() => copy(flow, "raw_response")}>
                {t("header.flowMenu.copyRawResponse")}
            </MenuItem>
            <MenuItem onClick={() => copy(flow, "raw")}>
                {t("header.flowMenu.copyRawCombined")}
            </MenuItem>
            <MenuItem onClick={() => copy(flow, "curl")}>{t("header.flowMenu.copyAsCurl")}</MenuItem>
            <MenuItem onClick={() => copy(flow, "httpie")}>
                {t("header.flowMenu.copyAsHttpie")}
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
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    return (
        <Dropdown
            className=""
            text={
                <Button
                    title={t("header.flowMenu.markTooltip")}
                    icon="fa-paint-brush text-success"
                    onClick={() => 1}
                >
                    {t("header.flowMenu.mark")}▾
                </Button>
            }
            options={{ placement: "bottom-start" }}
        >
            <MenuItem onClick={() => dispatch(markFlows(flows, ""))}>
                {t("header.flowMenu.noMarker")}
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
