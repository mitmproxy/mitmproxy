import * as React from "react";
import { formatTimeStamp } from "../../utils";
import { Address, Client, Flow, Server } from "../../flow";

type ConnectionInfoProps = {
    conn: Client | Server;
};

export function formatAddress(
    desc: string,
    address: Address | undefined,
): React.ReactElement {
    if (address === undefined) {
        return <></>;
    }
    // strip IPv6 flowid
    address = [address[0], address[1]];
    // Add IPv6 brackets
    if (address[0].includes(":")) {
        address[0] = `[${address[0]}]`;
    }
    return (
        <tr>
            <td>{desc}:</td>
            <td>{address.join(":")}</td>
        </tr>
    );
}

export function ConnectionInfo({ conn }: ConnectionInfoProps) {
    let address_info: React.ReactElement;
    if ("address" in conn) {
        // Server
        address_info = (
            <>
                {formatAddress("Address", conn.address)}
                {formatAddress("Resolved address", conn.peername)}
                {formatAddress("Source address", conn.sockname)}
            </>
        );
    } else {
        // Client
        address_info = formatAddress("Address", conn.peername);
    }
    return (
        <table className="connection-table">
            <tbody>
                {address_info}
                {conn.sni ? (
                    <tr>
                        <td>
                            <abbr title="TLS Server Name Indication">SNI</abbr>:
                        </td>
                        <td>{conn.sni}</td>
                    </tr>
                ) : null}
                {conn.alpn ? (
                    <tr>
                        <td>
                            <abbr title="ALPN protocol negotiated">ALPN</abbr>:
                        </td>
                        <td>{conn.alpn}</td>
                    </tr>
                ) : null}
                {conn.tls_version ? (
                    <tr>
                        <td>TLS Version:</td>
                        <td>{conn.tls_version}</td>
                    </tr>
                ) : null}
                {conn.cipher ? (
                    <tr>
                        <td>TLS Cipher:</td>
                        <td>{conn.cipher}</td>
                    </tr>
                ) : null}
            </tbody>
        </table>
    );
}

function attrList(data: [string, string][]): React.ReactElement {
    return (
        <dl className="cert-attributes">
            {data.map(([k, v]) => (
                <React.Fragment key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                </React.Fragment>
            ))}
        </dl>
    );
}

export function CertificateInfo({ flow }: { flow: Flow }): React.ReactElement {
    const cert = flow.server_conn?.cert;
    if (!cert) return <></>;

    return (
        <>
            <h4 key="name">Server Certificate</h4>
            <table className="certificate-table">
                <tbody>
                    <tr>
                        <td>Type</td>
                        <td>
                            {cert.keyinfo[0]}, {cert.keyinfo[1]} bits
                        </td>
                    </tr>
                    <tr>
                        <td>SHA256 digest</td>
                        <td>{cert.sha256}</td>
                    </tr>
                    <tr>
                        <td>Valid from</td>
                        <td>
                            {formatTimeStamp(cert.notbefore, {
                                milliseconds: false,
                            })}
                        </td>
                    </tr>
                    <tr>
                        <td>Valid to</td>
                        <td>
                            {formatTimeStamp(cert.notafter, {
                                milliseconds: false,
                            })}
                        </td>
                    </tr>
                    <tr>
                        <td>Subject Alternative Names</td>
                        <td>{cert.altnames.join(", ")}</td>
                    </tr>
                    <tr>
                        <td>Subject</td>
                        <td>{attrList(cert.subject)}</td>
                    </tr>
                    <tr>
                        <td>Issuer</td>
                        <td>{attrList(cert.issuer)}</td>
                    </tr>
                    <tr>
                        <td>Serial</td>
                        <td>{cert.serial}</td>
                    </tr>
                </tbody>
            </table>
        </>
    );
}

export default function Connection({ flow }: { flow: Flow }) {
    return (
        <section className="detail">
            <h4>Client Connection</h4>
            <ConnectionInfo conn={flow.client_conn} />

            {flow.server_conn?.address && (
                <>
                    <h4>Server Connection</h4>
                    <ConnectionInfo conn={flow.server_conn} />
                </>
            )}

            <CertificateInfo flow={flow} />
        </section>
    );
}
Connection.displayName = "Connection";
