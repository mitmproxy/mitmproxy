import React from "react";
import _ from "lodash";

import {formatTimeStamp, formatTimeDelta} from "../../utils.js";

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

var Details = React.createClass({
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

export default Details;