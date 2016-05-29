import React from "react";
import {formatSize} from "../utils.js"
import {SettingsState} from "./common.js";

Footer.propTypes = {
    settings: React.PropTypes.object.isRequired,
};

export default function Footer({ settings }) {
    const {mode, intercept, showhost, no_upstream_cert, rawtcp, http2, anticache, anticomp, stickyauth, stickycookie, stream} = settings;
    return (
        <footer>
            {mode && mode != "regular" && (
                <span className="label label-success">{mode} mode</span>
            )}
            {intercept && (
                <span className="label label-success">Intercept: {intercept}</span>
            )}
            {showhost && (
                <span className="label label-success">showhost</span>
            )}
            {no_upstream_cert && (
                <span className="label label-success">no-upstream-cert</span>
            )}
             {rawtcp && (
                <span className="label label-success">raw-tcp</span>
            )}
            {!http2 && (
                <span className="label label-success">no-http2</span>
            )}
            {anticache && (
                <span className="label label-success">anticache</span>
            )}
            {anticomp  && (
                <span className="label label-success">anticomp</span>
            )}
            {stickyauth && (
                <span className="label label-success">stickyauth: {stickyauth}</span>
            )}
            {stickycookie && (
                <span className="label label-success">stickycookie: {stickycookie}</span>
            )}
            {stream && (
                <span className="label label-success">stream: {formatSize(stream)}</span>
            )}


        </footer>
    );
}
