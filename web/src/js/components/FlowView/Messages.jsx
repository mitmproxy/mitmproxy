import React, { Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'


import { RequestUtils, isValidHttpVersion, parseUrl } from '../../flow/utils.js'
import { formatTimeStamp } from '../../utils.js'
import ContentView from '../ContentView'
import ContentViewOptions from '../ContentView/ContentViewOptions'
import ValidateEditor from '../ValueEditor/ValidateEditor'
import ValueEditor from '../ValueEditor/ValueEditor'
import HideInStatic from '../common/HideInStatic'

import Headers from './Headers'
import { startEdit, updateEdit } from '../../ducks/ui/flow'
import * as FlowActions from '../../ducks/flows'
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
        flow: state.ui.flow.modifiedFlow || state.flows.byId[state.flows.selected[0]],
        isEdit: !!state.ui.flow.modifiedFlow,
    }),
    {
        updateFlow: updateEdit,
        uploadContent: FlowActions.uploadContent
    }
)

export class Request extends Component {
    render() {
        const { flow, isEdit, updateFlow, uploadContent } = this.props
        let noContent =  !isEdit && (flow.request.contentLength == 0 || flow.request.contentLength == null)
        return (
            <section className="request">
                <article>
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
                        message={flow.request}/>

                    <hr/>
                    <Headers
                        message={flow.request}
                        readonly={!isEdit}
                        onChange={trailers => updateFlow({ request: { trailers } })}
                        type='trailers'
                    />
                </article>
                <HideInStatic>
                {!noContent &&
                    <footer>
                        <ContentViewOptions
                            flow={flow}
                            readonly={!isEdit}
                            message={flow.request}
                            uploadContent={content => uploadContent(flow, content, "request")}/>
                    </footer>
                }
                </HideInStatic>
            </section>
        )
    }
}

Request = Message(Request)


export class Response extends Component {
    render() {
        const { flow, isEdit, updateFlow, uploadContent } = this.props
        let noContent =  !isEdit && (flow.response.contentLength == 0 || flow.response.contentLength == null)

        return (
            <section className="response">
                <article>
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
                        message={flow.response}
                    />
                    <hr/>
                    <Headers
                        message={flow.response}
                        readonly={!isEdit}
                        onChange={trailers => updateFlow({ response: { trailers } })}
                        type='trailers'
                    />
                </article>
                <HideInStatic>
                {!noContent &&
                    <footer >
                        <ContentViewOptions
                            flow={flow}
                            message={flow.response}
                            uploadContent={content => uploadContent(flow, content, "response")}
                            readonly={!isEdit}/>
                    </footer>
                }
                </HideInStatic>
            </section>
        )
    }
}

Response = Message(Response)


ErrorView.propTypes = {
    flow: PropTypes.object.isRequired,
}

export function ErrorView({ flow }) {
    return (
        <section className="error">
            <div className="alert alert-warning">
                {flow.error.msg}
                <div>
                    <small>{formatTimeStamp(flow.error.timestamp)}</small>
                </div>
            </div>
        </section>
    )
}
