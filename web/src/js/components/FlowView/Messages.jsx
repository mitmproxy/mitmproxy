import React, { Component } from 'react'
import _ from 'lodash'

import { FlowActions } from '../../actions.js'
import { RequestUtils, isValidHttpVersion, parseUrl, parseHttpVersion } from '../../flow/utils.js'
import { Key, formatTimeStamp } from '../../utils.js'
import ContentView from '../ContentView'
import ValueEditor from '../ValueEditor'
import Headers from './Headers'

class RequestLine extends Component {

    render() {
        const { flow } = this.props

        return (
            <div className="first-line request-line">
                <ValueEditor
                    ref="method"
                    content={flow.request.method}
                    onDone={method => FlowActions.update(flow, { request: { method } })}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="url"
                    content={RequestUtils.pretty_url(flow.request)}
                    onDone={url => FlowActions.update(flow, { request: Object.assign({ path: '' }, parseUrl(url)) })}
                    isValid={url => !!parseUrl(url).host}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="httpVersion"
                    content={flow.request.http_version}
                    onDone={ver => FlowActions.update(flow, { request: { http_version: parseHttpVersion(ver) } })}
                    isValid={isValidHttpVersion}
                    inline
                />
            </div>
        )
    }
}

class ResponseLine extends Component {

    render() {
        const { flow } = this.props

        return (
            <div className="first-line response-line">
                <ValueEditor
                    ref="httpVersion"
                    content={flow.response.http_version}
                    onDone={nextVer => FlowActions.update(flow, { response: { http_version: parseHttpVersion(nextVer) } })}
                    isValid={isValidHttpVersion}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="code"
                    content={flow.response.status_code + ''}
                    onDone={code => FlowActions.update(flow, { response: { code: parseInt(code) } })}
                    isValid={code => /^\d+$/.test(code)}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="msg"
                    content={flow.response.reason}
                    onDone={msg => FlowActions.update(flow, { response: { msg } })}
                    inline
                />
            </div>
        )
    }
}

export class Request extends Component {

    render() {
        const { flow } = this.props

        return (
            <section className="request">
                <RequestLine ref="requestLine" flow={flow}/>
                <Headers
                    ref="headers"
                    message={flow.request}
                    onChange={headers => FlowActions.update(flow, { request: { headers } })}
                />
                <hr/>
                <ContentView flow={flow} message={flow.request}/>
            </section>
        )
    }

    edit(k) {
        switch (k) {
            case 'm':
                this.refs.requestLine.refs.method.focus()
                break
            case 'u':
                this.refs.requestLine.refs.url.focus()
                break
            case 'v':
                this.refs.requestLine.refs.httpVersion.focus()
                break
            case 'h':
                this.refs.headers.edit()
                break
            default:
                throw new Error(`Unimplemented: ${k}`)
        }
    }
}

export class Response extends Component {

    render() {
        const { flow } = this.props

        return (
            <section className="response">
                <ResponseLine ref="responseLine" flow={flow}/>
                <Headers
                    ref="headers"
                    message={flow.response}
                    onChange={headers => FlowActions.update(flow, { response: { headers } })}
                />
                <hr/>
                <ContentView flow={flow} message={flow.response}/>
            </section>
        )
    }

    edit(k) {
        switch (k) {
            case 'c':
                this.refs.responseLine.refs.status_code.focus()
                break
            case 'm':
                this.refs.responseLine.refs.msg.focus()
                break
            case 'v':
                this.refs.responseLine.refs.httpVersion.focus()
                break
            case 'h':
                this.refs.headers.edit()
                break
            default:
                throw new Error(`'Unimplemented: ${k}`)
        }
    }
}

export function Error({ flow }) {
    return (
        <section>
            <div className="alert alert-warning">
                {flow.error.msg}
                <div>
                    <small>{formatTimeStamp(flow.error.timestamp)}</small>
                </div>
            </div>
        </section>
    )
}
