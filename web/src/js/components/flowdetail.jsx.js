var NavAction = React.createClass({
    onClick: function (e) {
        e.preventDefault();
        this.props.onClick();
    },
    render: function () {
        return (
            <a title={this.props.title}
                href="#"
                className="nav-action"
                onClick={this.onClick}>
                <i className={"fa fa-fw " + this.props.icon}></i>
            </a>
        );
    }
});

var FlowDetailNav = React.createClass({
    render: function () {
        var flow = this.props.flow;

        var tabs = this.props.tabs.map(function (e) {
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function (event) {
                this.props.selectTab(e);
                event.preventDefault();
            }.bind(this);
            return <a key={e}
                href="#"
                className={className}
                onClick={onClick}>{str}</a>;
        }.bind(this));

        var acceptButton = null;
        if(flow.intercepted){
            acceptButton = <NavAction title="[a]ccept intercepted flow" icon="fa-play" onClick={FlowActions.accept.bind(null, flow)} />
        }
        var revertButton = null;
        if(flow.modified){
            revertButton = <NavAction title="revert changes to flow [V]" icon="fa-history" onClick={FlowActions.revert.bind(null, flow)} />
        }

        return (
            <nav ref="head" className="nav-tabs nav-tabs-sm">
                {tabs}
                <NavAction title="[d]elete flow" icon="fa-trash" onClick={FlowActions.delete.bind(null, flow)} />
                <NavAction title="[D]uplicate flow" icon="fa-copy" onClick={FlowActions.duplicate.bind(null, flow)} />
                <NavAction disabled title="[r]eplay flow" icon="fa-repeat" onClick={FlowActions.replay.bind(null, flow)} />
                {acceptButton}
                {revertButton}
            </nav>
        );
    }
});

var Headers = React.createClass({
    render: function () {
        var rows = this.props.message.headers.map(function (header, i) {
            return (
                <tr key={i}>
                    <td className="header-name">{header[0] + ":"}</td>
                    <td className="header-value">{header[1]}</td>
                </tr>
            );
        });
        return (
            <table className="header-table">
                <tbody>
                    {rows}
                </tbody>
            </table>
        );
    }
});

var FlowDetailRequest = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            flow.request.method,
            RequestUtils.pretty_url(flow.request),
            "HTTP/" + flow.request.httpversion.join(".")
        ].join(" ");
        var content = null;
        if (flow.request.contentLength > 0) {
            content = "Request Content Size: " + formatSize(flow.request.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <div className="first-line">{ first_line }</div>
                <Headers message={flow.request}/>
                <hr/>
                {content}
            </section>
        );
    }
});

var FlowDetailResponse = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            "HTTP/" + flow.response.httpversion.join("."),
            flow.response.code,
            flow.response.msg
        ].join(" ");
        var content = null;
        if (flow.response.contentLength > 0) {
            content = "Response Content Size: " + formatSize(flow.response.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <div className="first-line">{ first_line }</div>
                <Headers message={flow.response}/>
                <hr/>
                {content}
            </section>
        );
    }
});

var FlowDetailError = React.createClass({
    render: function () {
        var flow = this.props.flow;
        return (
            <section>
                <div className="alert alert-warning">
                {flow.error.msg}
                    <div>
                        <small>{ formatTimeStamp(flow.error.timestamp) }</small>
                    </div>
                </div>
            </section>
        );
    }
});

var TimeStamp = React.createClass({
    render: function () {

        if (!this.props.t) {
            //should be return null, but that triggers a React bug.
            return <tr></tr>;
        }

        var ts = formatTimeStamp(this.props.t);

        var delta;
        if (this.props.deltaTo) {
            delta = formatTimeDelta(1000 * (this.props.t - this.props.deltaTo));
            delta = <span className="text-muted">{"(" + delta + ")"}</span>;
        } else {
            delta = null;
        }

        return <tr>
            <td>{this.props.title + ":"}</td>
            <td>{ts} {delta}</td>
        </tr>;
    }
});

var ConnectionInfo = React.createClass({

    render: function () {
        var conn = this.props.conn;
        var address = conn.address.address.join(":");

        var sni = <tr key="sni"></tr>; //should be null, but that triggers a React bug.
        if (conn.sni) {
            sni = <tr key="sni">
                <td>
                    <abbr title="TLS Server Name Indication">TLS SNI:</abbr>
                </td>
                <td>{conn.sni}</td>
            </tr>;
        }
        return (
            <table className="connection-table">
                <tbody>
                    <tr key="address">
                        <td>Address:</td>
                        <td>{address}</td>
                    </tr>
                    {sni}
                </tbody>
            </table>
        );
    }
});

var CertificateInfo = React.createClass({
    render: function () {
        //TODO: We should fetch human-readable certificate representation
        // from the server
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;

        var preStyle = {maxHeight: 100};
        return (
            <div>
            {client_conn.cert ? <h4>Client Certificate</h4> : null}
            {client_conn.cert ? <pre style={preStyle}>{client_conn.cert}</pre> : null}

            {server_conn.cert ? <h4>Server Certificate</h4> : null}
            {server_conn.cert ? <pre style={preStyle}>{server_conn.cert}</pre> : null}
            </div>
        );
    }
});

var Timing = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var sc = flow.server_conn;
        var cc = flow.client_conn;
        var req = flow.request;
        var resp = flow.response;

        var timestamps = [
            {
                title: "Server conn. initiated",
                t: sc.timestamp_start,
                deltaTo: req.timestamp_start
            }, {
                title: "Server conn. TCP handshake",
                t: sc.timestamp_tcp_setup,
                deltaTo: req.timestamp_start
            }, {
                title: "Server conn. SSL handshake",
                t: sc.timestamp_ssl_setup,
                deltaTo: req.timestamp_start
            }, {
                title: "Client conn. established",
                t: cc.timestamp_start,
                deltaTo: req.timestamp_start
            }, {
                title: "Client conn. SSL handshake",
                t: cc.timestamp_ssl_setup,
                deltaTo: req.timestamp_start
            }, {
                title: "First request byte",
                t: req.timestamp_start,
            }, {
                title: "Request complete",
                t: req.timestamp_end,
                deltaTo: req.timestamp_start
            }
        ];

        if (flow.response) {
            timestamps.push(
                {
                    title: "First response byte",
                    t: resp.timestamp_start,
                    deltaTo: req.timestamp_start
                }, {
                    title: "Response complete",
                    t: resp.timestamp_end,
                    deltaTo: req.timestamp_start
                }
            );
        }

        //Add unique key for each row.
        timestamps.forEach(function (e) {
            e.key = e.title;
        });

        timestamps = _.sortBy(timestamps, 't');

        var rows = timestamps.map(function (e) {
            return <TimeStamp {...e}/>;
        });

        return (
            <div>
                <h4>Timing</h4>
                <table className="timing-table">
                    <tbody>
                    {rows}
                    </tbody>
                </table>
            </div>
        );
    }
});

var FlowDetailConnectionInfo = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;
        return (
            <section>

                <h4>Client Connection</h4>
                <ConnectionInfo conn={client_conn}/>

                <h4>Server Connection</h4>
                <ConnectionInfo conn={server_conn}/>

                <CertificateInfo flow={flow}/>

                <Timing flow={flow}/>

            </section>
        );
    }
});

var allTabs = {
    request: FlowDetailRequest,
    response: FlowDetailResponse,
    error: FlowDetailError,
    details: FlowDetailConnectionInfo
};

var FlowDetail = React.createClass({
    mixins: [StickyHeadMixin, Navigation, State],
    getTabs: function (flow) {
        var tabs = [];
        ["request", "response", "error"].forEach(function (e) {
            if (flow[e]) {
                tabs.push(e);
            }
        });
        tabs.push("details");
        return tabs;
    },
    nextTab: function (i) {
        var tabs = this.getTabs(this.props.flow);
        var currentIndex = tabs.indexOf(this.getParams().detailTab);
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        var nextIndex = (currentIndex + i + tabs.length) % tabs.length;
        this.selectTab(tabs[nextIndex]);
    },
    selectTab: function (panel) {
        this.replaceWith(
            "flow",
            {
                flowId: this.getParams().flowId,
                detailTab: panel
            }
        );
    },
    render: function () {
        var flow = this.props.flow;
        var tabs = this.getTabs(flow);
        var active = this.getParams().detailTab;

        if (!_.contains(tabs, active)) {
            if (active === "response" && flow.error) {
                active = "error";
            } else if (active === "error" && flow.response) {
                active = "response";
            } else {
                active = tabs[0];
            }
            this.selectTab(active);
        }

        var Tab = allTabs[active];
        return (
            <div className="flow-detail" onScroll={this.adjustHead}>
                <FlowDetailNav ref="head"
                    flow={flow}
                    tabs={tabs}
                    active={active}
                    selectTab={this.selectTab}/>
                <Tab flow={flow}/>
            </div>
        );
    }
});