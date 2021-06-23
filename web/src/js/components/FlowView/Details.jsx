import React from 'react'
import _ from 'lodash'
import { formatTimeStamp, formatTimeDelta } from '../../utils.js'

export function TimeStamp({ t, deltaTo, title }) {
    return t ? (
        <tr>
            <td>{title}:</td>
            <td>
                {formatTimeStamp(t)}
                {deltaTo && (
                    <span className="text-muted">
                        ({formatTimeDelta(1000 * (t - deltaTo))})
                    </span>
                )}
            </td>
        </tr>
    ) : (
        <tr></tr>
    )
}

export function ConnectionInfo({ conn }) {
    return (
        <table className="connection-table">
            <tbody>
                    <tr key="address">
                    <td>Address:</td>
                    <td>{conn.address.join(':')}</td>
                </tr>
                {conn.sni && (
                    <tr key="sni">
                        <td><abbr title="TLS Server Name Indication">TLS SNI:</abbr></td>
                        <td>{conn.sni}</td>
                    </tr>
                )}
                {conn.tls_version && (
                    <tr key="tls_version">
                        <td>TLS version:</td>
                        <td>{conn.tls_version}</td>
                    </tr>
                )}
                {conn.cipher_name && (
                    <tr key="cipher_name">
                        <td>cipher name:</td>
                        <td>{conn.cipher_name}</td>
                    </tr>
                )}
                {conn.alpn_proto_negotiated && (
                    <tr key="ALPN">
                        <td><abbr title="ALPN protocol negotiated">ALPN:</abbr></td>
                        <td>{conn.alpn_proto_negotiated}</td>
                    </tr>
                )}
                {conn.ip_address && (
                    <tr key="ip_address">
                        <td>Resolved address:</td>
                        <td>{conn.ip_address.join(':')}</td>
                    </tr>
                )}
                {conn.source_address && (
                    <tr key="source_address">
                        <td>Source address:</td>
                        <td>{conn.source_address.join(':')}</td>
                    </tr>
                )}
            </tbody>
        </table>
    )
}

export function CertificateInfo({ flow }) {
    // @todo We should fetch human-readable certificate representation from the server
    return (
        <div>
            {flow.client_conn.cert && [
                <h4 key="name">Client Certificate</h4>,
                <pre key="value" style={{ maxHeight: 100 }}>{flow.client_conn.cert}</pre>
            ]}

            {flow.server_conn.cert && [
                <h4 key="name">Server Certificate</h4>,
                <pre key="value" style={{ maxHeight: 100 }}>{flow.server_conn.cert}</pre>
            ]}
        </div>
    )
}

export function Timing({ flow }) {
    const { server_conn: sc, client_conn: cc, request: req, response: res } = flow

    const timestamps = [
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
            t: req.timestamp_start
        }, {
            title: "Request complete",
            t: req.timestamp_end,
            deltaTo: req.timestamp_start
        }, res && {
            title: "First response byte",
            t: res.timestamp_start,
            deltaTo: req.timestamp_start
        }, res && {
            title: "Response complete",
            t: res.timestamp_end,
            deltaTo: req.timestamp_start
        }
    ]

    return (
        <div>
            <h4>Timing</h4>
            <table className="timing-table">
                <tbody>
                    {timestamps.filter(v => v).sort((a, b) => a.t - b.t).map(item => (
                        <TimeStamp key={item.title} {...item}/>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

export default function Details({ flow }) {
    return (
        <section className="detail">
            <h4>Client Connection</h4>
            <ConnectionInfo conn={flow.client_conn}/>

            {flow.server_conn.address &&
                    [
                        <h4 key="sc">Server Connection</h4>,
                        <ConnectionInfo key="sc-ci" conn={flow.server_conn}/>
                    ]
            }

            <CertificateInfo flow={flow}/>

            <Timing flow={flow}/>
        </section>
    )
}
