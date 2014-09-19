/** @jsx React.DOM */

var FlowDetailNav = React.createClass({
    render: function(){

        var items = this.props.tabs.map(function(e){
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function(){
                this.props.selectTab(e);
                return false;
            }.bind(this);
            return <a key={e}
                      href="#" 
                      className={className}
                      onClick={onClick}>{str}</a>;
        }.bind(this));
        return (
            <nav ref="head" className="nav-tabs nav-tabs-sm">
                {items}
            </nav>
        );
    } 
});

var Headers = React.createClass({
    render: function(){
        var rows = this.props.message.headers.map(function(header){
            return (
                <tr>
                    <td className="header-name">{header[0]+":"}</td>
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
    render: function(){
        var flow = this.props.flow;
        var first_line = [
                flow.request.method,
                RequestUtils.pretty_url(flow.request),
                "HTTP/"+ flow.response.httpversion.join(".")
            ].join(" ");
        var content = null;
        if(flow.request.contentLength > 0){
            content = "Request Content Size: "+ formatSize(flow.request.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <code>{ first_line }</code>
                <Headers message={flow.request}/>
                <hr/>
                {content}
            </section>
        );
    }
});

var FlowDetailResponse = React.createClass({
    render: function(){
        var flow = this.props.flow;
        var first_line = [
                "HTTP/"+ flow.response.httpversion.join("."),
                flow.response.code,
                flow.response.msg
            ].join(" ");
        var content = null;
        if(flow.response.contentLength > 0){
            content = "Response Content Size: "+ formatSize(flow.response.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <code>{ first_line }</code>
                <Headers message={flow.response}/>
                <hr/>
                {content}
            </section>
        );
    }
});

var TimeStamp = React.createClass({
    render: function() {
        var ts, delta;

        if(!this.props.t && this.props.optional){
            //should be return null, but that triggers a React bug.
            return <tr></tr>;
        } else if (!this.props.t){
            ts = "active";
        } else {
            ts = (new Date(this.props.t * 1000)).toISOString();
            ts = ts.replace("T", " ").replace("Z","");

            if(this.props.deltaTo){
                delta = Math.round((this.props.t-this.props.deltaTo)*1000) + "ms";
                delta = <span className="text-muted">{"(" + delta + ")"}</span>;
            } else {
                delta = null;
            }
        }

        return <tr><td>{this.props.title + ":"}</td><td>{ts} {delta}</td></tr>;
    }
});

var ConnectionInfo = React.createClass({

    render: function() {
        var conn = this.props.conn;
        var address = conn.address.address.join(":");

        var sni = <tr key="sni"></tr>; //should be null, but that triggers a React bug.
        if(conn.sni){
            sni = <tr key="sni"><td><abbr title="TLS Server Name Indication">TLS SNI:</abbr></td><td>{conn.sni}</td></tr>;
        }
        return (
            <table className="connection-table">
                <tbody>
                    <tr key="address"><td>Address:</td><td>{address}</td></tr>
                    {sni}
                    <TimeStamp title="Start time"
                               key="start"
                               t={conn.timestamp_start} />
                    <TimeStamp title="TCP Setup"
                               key="tcpsetup"
                               t={conn.timestamp_tcp_setup}
                               deltaTo={conn.timestamp_start}
                               optional={true} />
                    <TimeStamp title="SSL handshake"
                               key="sslsetup"
                               t={conn.timestamp_ssl_setup}
                               deltaTo={conn.timestamp_start}
                               optional={true} />
                    <TimeStamp title="End time"
                               key="end"
                               t={conn.timestamp_end}
                               deltaTo={conn.timestamp_start} />
                </tbody>
            </table>
        );
    }
});

var CertificateInfo = React.createClass({
    render: function(){
        //TODO: We should fetch human-readable certificate representation
        // from the server
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;
        return (
            <div>
            {client_conn.cert ? <h4>Client Certificate</h4> : null}
            {client_conn.cert ? <pre>{client_conn.cert}</pre> : null}

            {server_conn.cert ? <h4>Server Certificate</h4> : null}
            {server_conn.cert ? <pre>{server_conn.cert}</pre> : null}
            </div>
        );
    }
});

var FlowDetailConnectionInfo = React.createClass({
    render: function(){
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

            </section>
        );
    }
});

var tabs = {
    request: FlowDetailRequest,
    response: FlowDetailResponse,
    details: FlowDetailConnectionInfo
};

var FlowDetail = React.createClass({
    getDefaultProps: function(){
        return {
            tabs: ["request","response", "details"]
        };
    },
    mixins: [StickyHeadMixin],
    nextTab: function(i) {
        var currentIndex = this.props.tabs.indexOf(this.props.active);
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        var nextIndex = (currentIndex + i + this.props.tabs.length) % this.props.tabs.length;
        this.props.selectTab(this.props.tabs[nextIndex]);
    },
    render: function(){
        var flow = JSON.stringify(this.props.flow, null, 2);
        var Tab = tabs[this.props.active];
        return (
            <div className="flow-detail" onScroll={this.adjustHead}>
                <FlowDetailNav ref="head"
                               tabs={this.props.tabs}
                               active={this.props.active}
                               selectTab={this.props.selectTab}/>
                <Tab flow={this.props.flow}/>
            </div>
            );
    } 
});