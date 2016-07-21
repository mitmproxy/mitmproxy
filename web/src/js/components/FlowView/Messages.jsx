import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'


import { RequestUtils, isValidHttpVersion, parseUrl } from '../../flow/utils.js'
import { formatTimeStamp } from '../../utils.js'
import ContentView from '../ContentView'
import ValidateEditor from '../ValueEditor/ValidateEditor'
import ValueEditor from '../ValueEditor/ValueEditor'

import Headers from './Headers'
import { startEdit, updateEdit, uploadContent } from '../../ducks/ui/flow'
import ToggleEdit from './ToggleEdit'

function RequestLine({ flow, readonly, updateFlow }) {
    return (
        <div className="first-line request-line">
            <div>
                <ValueEditor
                    content={flow.request.method}
                    readonly={readonly}
                    onDone={method => updateFlow({ request: { method } })}
                />
                &nbsp;
                <ValidateEditor
                    content={RequestUtils.pretty_url(flow.request)}
                    readonly={readonly}
                    onDone={url => updateFlow({ request: {path: '', ...parseUrl(url)}})}
                    isValid={url => !!parseUrl(url).host}
                />
                &nbsp;
                <ValidateEditor
                    content={flow.request.http_version}
                    readonly={readonly}
                    onDone={http_version => updateFlow({ request: { http_version } })}
                    isValid={isValidHttpVersion}
                />
            </div>
        </div>
    )
}

function ResponseLine({ flow, readonly, updateFlow }) {
    return (
        <div className="first-line response-line">
            <ValidateEditor
                content={flow.response.http_version}
                readonly={readonly}
                onDone={nextVer => updateFlow({ response: { http_version: nextVer } })}
                isValid={isValidHttpVersion}
            />
            &nbsp;
            <ValidateEditor
                content={flow.response.status_code + ''}
                readonly={readonly}
                onDone={code => updateFlow({ response: { code: parseInt(code) } })}
                isValid={code => /^\d+$/.test(code)}
            />
            &nbsp;
            <ValueEditor
                content={flow.response.reason}
                readonly={readonly}
                onDone={msg => updateFlow({ response: { msg } })}
            />
        </div>
    )
}

const Message = connect(
    state => ({
        flow: state.flows.byId[state.flows.selected[0]],
        isEdit: !!state.ui.flow.modifiedFlow,
    }),
    {
        updateFlow: updateEdit,
        uploadContent: uploadContent
    }
)

export class Request extends Component {
    render() {
        const { flow, isEdit, updateFlow, uploadContent } = this.props

        return (
            <section className="request">
                <ToggleEdit/>
                <RequestLine
                    flow={flow}
                    readonly={!isEdit}
                    updateFlow={updateFlow}/>
                <Headers
                    message={flow.request}
                    readonly={!isEdit}
                    onChange={headers => updateFlow({ request: { headers } })}
                />

                <hr/>
                <ContentView
                    readonly={!isEdit}
                    flow={flow}
                    onContentChange={content => updateFlow({ request: {content}})}
                    uploadContent={content => uploadContent(flow, content, "request")}
                    message={flow.request}/>
            </section>
        )
    }


    edit(k) {
        throw "unimplemented"
        /*
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
         */
    }

}

Request = Message(Request)


export class Response extends Component {
    render() {
        const { flow, isEdit, updateFlow, uploadContent } = this.props

        return (
            <section className="response">
                <ToggleEdit/>
                <ResponseLine
                    flow={flow}
                    readonly={!isEdit}
                    updateFlow={updateFlow}/>
                <Headers
                    message={flow.response}
                    readonly={!isEdit}
                    onChange={headers => updateFlow({ response: { headers } })}
                />
                <hr/>
                <ContentView
                    readonly={!isEdit}
                    flow={flow}
                    onContentChange={content => updateFlow({ response: {content}})}
                    uploadContent={content => uploadContent(flow, content, "response")}
                    message={flow.response}
                />
            </section>
        )
    }

    edit(k) {
        throw "unimplemented"
        /*
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
         */
    }
}

Response = Message(Response)


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
