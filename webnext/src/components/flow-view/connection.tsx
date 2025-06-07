import type { TabProps } from "@/components/flow-view/panel-tabs";
import { Section, SectionTitle } from "./section";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { Fragment, type ReactElement } from "react";
import type { Address, Certificate, Client, Server } from "web/flow";
import { formatTimeStamp } from "web/utils";

export function Connection({ flow }: TabProps) {
  return (
    <div className="space-y-4">
      <Section>
        <SectionTitle>Client connection</SectionTitle>
        <ConnectionInfo conn={flow.client_conn} />
      </Section>

      {flow.server_conn?.address && (
        <Section>
          <SectionTitle>Server connection</SectionTitle>
          <ConnectionInfo conn={flow.server_conn} />
        </Section>
      )}

      {flow.server_conn?.cert && (
        <Section>
          <SectionTitle>Server certificate</SectionTitle>
          <CertificateInfo certificate={flow.server_conn.cert} />
        </Section>
      )}
    </div>
  );
}

function ConnectionInfo({ conn }: { conn: Client | Server }) {
  return (
    <Table>
      <TableBody>
        {"address" in conn ? (
          <>
            {conn.address && (
              <AddressRow desc="Address" address={conn.address} />
            )}
            {conn.peername && (
              <AddressRow desc="Resolved address" address={conn.peername} />
            )}
            {conn.sockname && (
              <AddressRow desc="Source address" address={conn.sockname} />
            )}
          </>
        ) : (
          <>
            {conn.peername && (
              <AddressRow desc="Address" address={conn.peername} />
            )}
          </>
        )}
        {conn.sni && (
          <TableRow>
            <TableCell variant="muted">SNI:</TableCell>
            <TableCell variant="muted" className="flex-1">
              {conn.sni}
            </TableCell>
          </TableRow>
        )}
        {conn.alpn && (
          <TableRow>
            <TableCell variant="muted">ALPN:</TableCell>
            <TableCell variant="muted" className="flex-1">
              {conn.alpn}
            </TableCell>
          </TableRow>
        )}
        {conn.tls_version && (
          <TableRow>
            <TableCell variant="muted">TLS version:</TableCell>
            <TableCell variant="muted" className="flex-1">
              {conn.tls_version}
            </TableCell>
          </TableRow>
        )}
        {conn.cipher && (
          <TableRow>
            <TableCell variant="muted">TLS cipher:</TableCell>
            <TableCell variant="muted" className="flex-1">
              {conn.cipher}
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function AddressRow({
  desc,
  address,
}: {
  desc: string;
  address: Address;
}): ReactElement {
  // strip IPv6 flowid
  address = [address[0], address[1]];
  // Add IPv6 brackets
  if (address[0].includes(":")) {
    address[0] = `[${address[0]}]`;
  }

  return (
    <TableRow>
      <TableCell variant="muted">{desc}:</TableCell>
      <TableCell variant="muted" className="flex-1">
        {address.join(":")}
      </TableCell>
    </TableRow>
  );
}

function CertificateInfo({ certificate }: { certificate: Certificate }) {
  return (
    <Table>
      <TableBody>
        <TableRow>
          <TableCell variant="muted">Type:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {certificate.keyinfo[0]}, {certificate.keyinfo[1]} bits
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell variant="muted">SHA256 digest:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {certificate.sha256}
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell variant="muted">Valid from:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {formatTimeStamp(certificate.notbefore, {
              milliseconds: false,
            })}
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell variant="muted">Valid to:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {formatTimeStamp(certificate.notafter, {
              milliseconds: false,
            })}
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell variant="muted">Subject Alternative Names:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {certificate.altnames.join(", ")}
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell variant="muted">Subject:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {attrList(certificate.subject)}
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell variant="muted">Issuer:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {attrList(certificate.issuer)}
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell variant="muted">Serial:</TableCell>
          <TableCell variant="muted" className="flex-1">
            {certificate.serial}
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
}

function attrList(data: [string, string][]): React.ReactElement {
  return (
    <dl className="flex max-w-lg flex-wrap">
      {data.map(([k, v]) => (
        <Fragment key={k}>
          <dt className="flex-1/5 font-semibold">{k}</dt>
          <dd className="flex-4/5">{v}</dd>
        </Fragment>
      ))}
    </dl>
  );
}
