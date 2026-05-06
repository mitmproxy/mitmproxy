import * as React from "react";
import { useTranslation } from "react-i18next";
import { formatTimeStamp } from "../../utils";
import type { Address, Client, Flow, Server } from "../../flow";

type ConnectionInfoProps = {
    conn: Client | Server;
};

export function formatAddress(
    desc: string,
    address: Address | undefined | null,
): React.ReactElement {
    if (!address) {
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
    const { t } = useTranslation();
    let address_info: React.ReactElement;
    if ("address" in conn) {
        // Server
        address_info = (
            <>
                {formatAddress(t("flowView.connection.address"), conn.address)}
                {formatAddress(
                    t("flowView.connection.resolvedAddress"),
                    conn.peername,
                )}
                {formatAddress(
                    t("flowView.connection.sourceAddress"),
                    conn.sockname,
                )}
            </>
        );
    } else {
        // Client
        address_info = formatAddress(
            t("flowView.connection.address"),
            conn.peername,
        );
    }
    return (
        <table className="connection-table">
            <tbody>
                {address_info}
                {conn.sni ? (
                    <tr>
                        <td>
                            <abbr title={t("flowView.connection.sniTitle")}>
                                {t("flowView.connection.sni")}:
                            </abbr>
                        </td>
                        <td>{conn.sni}</td>
                    </tr>
                ) : null}
                {conn.alpn ? (
                    <tr>
                        <td>
                            <abbr title={t("flowView.connection.alpnTitle")}>
                                {t("flowView.connection.alpn")}:
                            </abbr>
                        </td>
                        <td>{conn.alpn}</td>
                    </tr>
                ) : null}
                {conn.tls_version ? (
                    <tr>
                        <td>{t("flowView.connection.tlsVersion")}:</td>
                        <td>{conn.tls_version}</td>
                    </tr>
                ) : null}
                {conn.cipher ? (
                    <tr>
                        <td>{t("flowView.connection.tlsCipher")}:</td>
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
    const { t } = useTranslation();
    const cert = flow.server_conn?.cert;
    if (!cert) return <></>;

    return (
        <>
            <h4 key="name">{t("flowView.connection.serverCertificate")}</h4>
            <table className="certificate-table">
                <tbody>
                    <tr>
                        <td>{t("flowView.connection.type")}</td>
                        <td>
                            {cert.keyinfo[0]}, {cert.keyinfo[1]}{" "}
                            {t("flowView.connection.bits")}
                        </td>
                    </tr>
                    <tr>
                        <td>{t("flowView.connection.sha256Digest")}</td>
                        <td>{cert.sha256}</td>
                    </tr>
                    <tr>
                        <td>{t("flowView.connection.validFrom")}</td>
                        <td>
                            {formatTimeStamp(cert.notbefore, {
                                includeMilliseconds: false,
                            })}
                        </td>
                    </tr>
                    <tr>
                        <td>{t("flowView.connection.validTo")}</td>
                        <td>
                            {formatTimeStamp(cert.notafter, {
                                includeMilliseconds: false,
                            })}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            {t("flowView.connection.subjectAlternativeNames")}
                        </td>
                        <td>{cert.altnames.join(", ")}</td>
                    </tr>
                    <tr>
                        <td>{t("flowView.connection.subject")}</td>
                        <td>{attrList(cert.subject)}</td>
                    </tr>
                    <tr>
                        <td>{t("flowView.connection.issuer")}</td>
                        <td>{attrList(cert.issuer)}</td>
                    </tr>
                    <tr>
                        <td>{t("flowView.connection.serial")}</td>
                        <td>{cert.serial}</td>
                    </tr>
                </tbody>
            </table>
        </>
    );
}

export default function Connection({ flow }: { flow: Flow }) {
    const { t } = useTranslation();
    return (
        <section className="detail">
            <h4>{t("flowView.connection.clientConnection")}</h4>
            <ConnectionInfo conn={flow.client_conn} />

            {flow.server_conn?.address && (
                <>
                    <h4>{t("flowView.connection.serverConnection")}</h4>
                    <ConnectionInfo conn={flow.server_conn} />
                </>
            )}

            <CertificateInfo flow={flow} />
        </section>
    );
}
Connection.displayName = "Connection";
