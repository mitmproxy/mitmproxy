import React, { ReactElement, type JSX } from "react";
import { useAppDispatch, useAppSelector } from "../../ducks";
import classnames from "classnames";
import {
    canReplay,
    endTime,
    getTotalSize,
    startTime,
    sortFunctions,
    getIcon,
    mainPath,
    statusCode,
    getMethod,
    getVersion,
} from "../../flow/utils";
import { formatSize, formatTimeDelta, formatTimeStamp } from "../../utils";
import * as flowActions from "../../ducks/flows";
import { Flow } from "../../flow";

type FlowColumnProps = {
    flow: Flow;
};

interface FlowColumn {
    (props: FlowColumnProps): JSX.Element;

    headerName: string; // Shown in the UI
}

export const tls: FlowColumn = ({ flow }) => {
    return (
        <td
            className={classnames(
                "col-tls",
                flow.client_conn.tls_established
                    ? "col-tls-https"
                    : "col-tls-http",
            )}
        />
    );
};
tls.headerName = "";

export const index: FlowColumn = ({ flow }) => {
    const index = useAppSelector((state) => state.flows.listIndex[flow.id]);
    return <td className="col-index">{index + 1}</td>;
};
index.headerName = "#";

export const icon: FlowColumn = ({ flow }) => {
    return (
        <td className="col-icon">
            <div className={classnames("resource-icon", getIcon(flow))} />
        </td>
    );
};
icon.headerName = "";

export const path: FlowColumn = ({ flow }) => {
    let err;
    if (flow.error) {
        if (flow.error.msg === "Connection killed.") {
            err = <i className="fa fa-fw fa-times pull-right" />;
        } else {
            err = <i className="fa fa-fw fa-exclamation pull-right" />;
        }
    }
    return (
        <td className="col-path">
            {flow.is_replay === "request" && (
                <i className="fa fa-fw fa-repeat pull-right" />
            )}
            {flow.intercepted && <i className="fa fa-fw fa-pause pull-right" />}
            {err}
            <span className="marker pull-right">{flow.marked}</span>
            {mainPath(flow)}
        </td>
    );
};
path.headerName = "Path";

export const method: FlowColumn = ({ flow }) => (
    <td className="col-method">{getMethod(flow)}</td>
);
method.headerName = "Method";

export const version: FlowColumn = ({ flow }) => (
    <td className="col-http-version">{getVersion(flow)}</td>
);
version.headerName = "Version";

export const status: FlowColumn = ({ flow }) => {
    let color = "darkred";

    if ((flow.type !== "http" && flow.type != "dns") || !flow.response)
        return <td className="col-status" />;

    if (100 <= flow.response.status_code && flow.response.status_code < 200) {
        color = "green";
    } else if (
        200 <= flow.response.status_code &&
        flow.response.status_code < 300
    ) {
        color = "darkgreen";
    } else if (
        300 <= flow.response.status_code &&
        flow.response.status_code < 400
    ) {
        color = "lightblue";
    } else if (
        400 <= flow.response.status_code &&
        flow.response.status_code < 500
    ) {
        color = "red";
    } else if (
        500 <= flow.response.status_code &&
        flow.response.status_code < 600
    ) {
        color = "red";
    }

    return (
        <td className="col-status" style={{ color: color }}>
            {statusCode(flow)}
        </td>
    );
};
status.headerName = "Status";

export const size: FlowColumn = ({ flow }) => {
    return <td className="col-size">{formatSize(getTotalSize(flow))}</td>;
};
size.headerName = "Size";

export const time: FlowColumn = ({ flow }) => {
    const start = startTime(flow);
    const end = endTime(flow);
    return (
        <td className="col-time">
            {start && end ? formatTimeDelta(1000 * (end - start)) : "..."}
        </td>
    );
};
time.headerName = "Time";

export const timestamp: FlowColumn = ({ flow }) => {
    const start = startTime(flow);
    return (
        <td className="col-timestamp">
            {start ? formatTimeStamp(start) : "..."}
        </td>
    );
};
timestamp.headerName = "Start time";

export const quickactions: FlowColumn = ({ flow }) => {
    const dispatch = useAppDispatch();

    let resume_or_replay: ReactElement<any> | null = null;
    if (flow.intercepted) {
        resume_or_replay = (
            <a
                href="#"
                className="quickaction"
                onClick={() => dispatch(flowActions.resume([flow]))}
            >
                <i className="fa fa-fw fa-play text-success" />
            </a>
        );
    } else if (canReplay(flow)) {
        resume_or_replay = (
            <a
                href="#"
                className="quickaction"
                onClick={() => dispatch(flowActions.replay([flow]))}
            >
                <i className="fa fa-fw fa-repeat text-primary" />
            </a>
        );
    }

    return (
        <td className="col-quickactions">
            {resume_or_replay ? <div>{resume_or_replay}</div> : <></>}
        </td>
    );
};
quickactions.headerName = "";

export const comment: FlowColumn = ({ flow }) => {
    const text = flow.comment;
    return <td className="col-comment">{text}</td>;
};
comment.headerName = "Comment";

const FlowColumns: { [key in keyof typeof sortFunctions]: FlowColumn } = {
    // parsed by web/gen/web_columns
    icon,
    index,
    method,
    version,
    path,
    quickactions,
    size,
    status,
    time,
    timestamp,
    tls,
    comment,
};
export default FlowColumns;
