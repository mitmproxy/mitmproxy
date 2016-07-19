import React, { Component, PropTypes } from 'react'
import _ from 'lodash'

import { RequestUtils, isValidHttpVersion, parseUrl, parseHttpVersion } from '../../flow/utils.js'
import { Key, formatTimeStamp } from '../../utils.js'
import ContentView from '../ContentView'
import ValueEditor from '../ValueEditor'
import Headers from './Headers'
import * as flowActions  from '../../ducks/flows'
import FlowEditorButton from './FlowEditorButton.jsx'


class RequestLine extends Component {

    render() {
        const { flow, updateFlow } = this.props

        return (
            <div className="first-line request-line">
                <ValueEditor
                    ref="method"
                    content={flow.request.method}
                    onDone={method => updateFlow({ request: { method } })}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="url"
                    content={RequestUtils.pretty_url(flow.request)}
                    onDone={url => updateFlow({ request: Object.assign({ path: '' }, parseUrl(url)) })}
                    isValid={url => !!parseUrl(url).host}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="httpVersion"
                    content={flow.request.http_version}
                    onDone={ver => updateFlow({ request: { http_version: parseHttpVersion(ver) } })}
                    isValid={isValidHttpVersion}
                    inline
                />
            </div>
        )
    }
}

class ResponseLine extends Component {

    render() {
        const { flow, updateFlow } = this.props

        return (
            <div className="first-line response-line">
                <ValueEditor
                    ref="httpVersion"
                    content={flow.response.http_version}
                    onDone={nextVer => updateFlow({ response: { http_version: parseHttpVersion(nextVer) } })}
                    isValid={isValidHttpVersion}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="code"
                    content={flow.response.status_code + ''}
                    onDone={code => updateFlow({ response: { code: parseInt(code) } })}
                    isValid={code => /^\d+$/.test(code)}
                    inline
                />
                &nbsp;
                <ValueEditor
                    ref="msg"
                    content={flow.response.reason}
                    onDone={msg => updateFlow({ response: { msg } })}
                    inline
                />
            </div>
        )
    }
}

export class Request extends Component {
   render() {
        const { flow, updateFlow } = this.props
        let onContentChange = content => flowActions.updateContent(this.props.flow, content, "request")

        return (
            <section className="request">
                <FlowEditorButton onContentChange={onContentChange}/>
                <RequestLine ref="requestLine" flow={flow} updateFlow={updateFlow} />
                <Headers
                    ref="headers"
                    message={flow.request}
                    onChange={headers => updateFlow({ request: { headers } })}
                />

                <hr/>
                <ContentView flow={flow}
                             onContentChange={onContentChange}
                             message={flow.request}
                />
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
        const { flow, updateFlow } = this.props
        let onContentChange = content => flowActions.updateContent(this.props.flow, content, "response")

        return (
            <section className="response">
                <FlowEditorButton onContentChange={onContentChange}/>
                <ResponseLine ref="responseLine" flow={flow} updateFlow={updateFlow} />
                <Headers
                    ref="headers"
                    message={flow.response}
                    onChange={headers => updateFlow({ response: { headers } })}
                />
                <hr/>
                <ContentView flow={flow}
                             onContentChange={onContentChange}
                             message={flow.response}
                />
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

ErrorView.propTypes = {
    flow: PropTypes.object.isRequired,
}

export function ErrorView({ flow }) {
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
