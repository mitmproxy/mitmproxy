/*
Type definitions for flows. Sync with mitmproxy/tools/web/app.py.
 */
interface _Flow {
    id: string
    intercepted: boolean
    is_replay?: "request" | "response"
    type: string
    modified: boolean
    marked: string
    client_conn: Client
    server_conn?: Server
    error?: Error
}

export type Flow = HTTPFlow | TCPFlow;

export interface HTTPFlow extends _Flow {
    type: "http"
    request: HTTPRequest
    response?: HTTPResponse
}

export interface TCPFlow extends _Flow {
    type: "tcp"
}

export interface Error {
    msg: string
    timestamp: number
}

export type Address = [string, number];

export interface Connection {
    id: string
    peername?: Address
    sockname?: Address

    tls_established: boolean
    sni?: string | boolean
    cipher?: string
    alpn?: string
    tls_version?: string

    timestamp_start?: number
    timestamp_tls_setup?: number
    timestamp_end?: number

}

export interface Client extends Connection {
    peername: Address
    sockname: Address
    timestamp_start: number
}

export interface Server extends Connection {
    address?: Address
}

export type Headers = [string, string][];

export interface HTTPMessage {
    http_version: string
    headers: Headers
    trailers?: Headers
    contentLength: number
    contentHash: string
    content?: string
    timestamp_start: number
    timestamp_end?: number
}

export interface HTTPRequest extends HTTPMessage {
    method: string
    scheme: string
    host: string
    port: number
    path: string
    pretty_host: string
}

export interface HTTPResponse extends HTTPMessage {
    status_code: number
    reason: string
}
