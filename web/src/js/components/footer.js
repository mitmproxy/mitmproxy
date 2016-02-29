import React from "react";
import {SettingsState} from "./common.js";

var Footer = React.createClass({
    mixins: [SettingsState],
    render: function () {
        var mode = this.state.settings.mode;
        var intercept = this.state.settings.intercept;
        return (
            <footer>
                {mode && mode != "regular" ? <span className="label label-success">{mode} mode</span> : null}
                &nbsp;
                {intercept ? <span className="label label-success">Intercept: {intercept}</span> : null}
            </footer>
        );
    }
});

export default Footer;