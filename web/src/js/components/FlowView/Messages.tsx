import React from 'react'

import { RequestUtils, isValidHttpVersion, parseUrl } from '../../flow/utils'
import { formatTimeStamp } from '../../utils'
import ContentView from '../ContentView'
import ContentViewOptions from '../ContentView/ContentViewOptions'
import ValidateEditor from '../ValueEditor/ValidateEditor'
import ValueEditor from '../ValueEditor/ValueEditor'
import HideInStatic from '../common/HideInStatic'

import Headers from './Headers'
import { updateEdit as updateFlow } from '../../ducks/ui/flow'
import { uploadContent } from '../../ducks/flows'
import ToggleEdit from './ToggleEdit'
import { useAppDispatch, useAppSelector } from "../../ducks";
import { HTTPFlow, HTTPMessage } from '../../flow'


type RequestLineProps = {
    flow: HTTPFlow,
    readonly: boolean,
}

function RequestLine({ flow, readonly }: RequestLineProps) {
    const dispatch = useAppDispatch()

    return (
        <div className="first-line request-line">
            <div>
                <ValueEditor
                    content={flow.request.method}
                    readonly={readonly}
                    onDone={method => dispatch(updateFlow({ request: { method } }))}
                />
                &nbsp;
                <ValidateEditor
                    content={RequestUtils.pretty_url(flow.request)}
                    readonly={readonly}
                    onDone={url => dispatch(updateFlow({ request: {path: '', ...parseUrl(url)}}))}
                    isValid={url => !!parseUrl(url).host}
                />
                &nbsp;
                <ValidateEditor
                    content={flow.request.http_version}
                    readonly={readonly}
                    onDone={http_version => dispatch(updateFlow({ request: { http_version } }))}
                    isValid={isValidHttpVersion}
                />
            </div>
        </div>
    )
}

type ResponseLineProps = {
    flow: HTTPFlow,
    readonly: boolean,
}

function ResponseLine({ flow, readonly }: ResponseLineProps) {
    const dispatch = useAppDispatch()

    return (
        <div className="first-line response-line">
            <ValidateEditor
                content={flow.response?.http_version}
                readonly={readonly}
                onDone={nextVer => dispatch(updateFlow({ response: { http_version: nextVer } }))}
                isValid={isValidHttpVersion}
            />
            &nbsp;
            <ValidateEditor
                content={flow.response?.status_code + ''}
                readonly={readonly}
                onDone={code => dispatch(updateFlow({ response: { code: parseInt(code) } }))}
                isValid={code => /^\d+$/.test(code)}
            />
            &nbsp;
            <ValueEditor
                content={flow.response?.reason}
                readonly={readonly}
                onDone={msg => dispatch(updateFlow({ response: { msg } }))}
            />
        </div>
    )
}

export function Request() {
    const dispatch = useAppDispatch(),
    flow = useAppSelector(state => state.ui.flow.modifiedFlow || state.flows.byId[state.flows.selected[0]]),
    isEdit = useAppSelector(state => !!state.ui.flow.modifiedFlow)

    let noContent =  !isEdit && (flow.request.contentLength == 0 || flow.request.contentLength == null)
    return (
        <section className="request">
            <article>
                <ToggleEdit/>
                <RequestLine
                    flow={flow}
                    readonly={!isEdit} />
                <Headers
                    message={flow.request}
                    readonly={!isEdit}
                    onChange={headers => dispatch(updateFlow({ request: { headers } }))}
                />

                <hr/>
                <ContentView
                    readonly={!isEdit}
                    flow={flow}
                    onContentChange={content => dispatch(updateFlow({ request: {content}}))}
                    message={flow.request}/>

                <hr/>
                <Headers
                    message={flow.request}
                    readonly={!isEdit}
                    onChange={trailers => dispatch(updateFlow({ request: { trailers } }))}
                    type='trailers'
                />
            </article>
            <HideInStatic>
            {!noContent &&
                <footer>
                    <ContentViewOptions
                        flow={flow}
                        message={flow.request}
                        uploadContent={content => dispatch(uploadContent(flow, content, "request"))}/>
                </footer>
            }
            </HideInStatic>
        </section>
    )
}

export function Response() {
    const dispatch = useAppDispatch(),
    flow = useAppSelector(state => state.ui.flow.modifiedFlow || state.flows.byId[state.flows.selected[0]]),
    isEdit = useAppSelector(state => !!state.ui.flow.modifiedFlow)

    let noContent =  !isEdit && (flow.response.contentLength == 0 || flow.response.contentLength == null)

    return (
        <section className="response">
            <article>
                <ToggleEdit/>
                <ResponseLine
                    flow={flow}
                    readonly={!isEdit} />
                <Headers
                    message={flow.response}
                    readonly={!isEdit}
                    onChange={headers => dispatch(updateFlow({ response: { headers } }))}
                />
                <hr/>
                <ContentView
                    readonly={!isEdit}
                    flow={flow}
                    onContentChange={content => dispatch(updateFlow({ response: {content}}))}
                    message={flow.response}
                />
                <hr/>
                <Headers
                    message={flow.response}
                    readonly={!isEdit}
                    onChange={trailers => dispatch(updateFlow({ response: { trailers } }))}
                    type='trailers'
                />
            </article>
            <HideInStatic>
            {!noContent &&
                <footer >
                    <ContentViewOptions
                        flow={flow}
                        message={flow.response}
                        uploadContent={content => dispatch(uploadContent(flow, content, "response"))} />
                </footer>
            }
            </HideInStatic>
        </section>
    )
}

type ErrorViewProps = {
    flow: HTTPFlow
}

export function ErrorView({ flow }: ErrorViewProps) {
    return (
        <section className="error">
            <div className="alert alert-warning">
                {flow.error?.msg}
                <div>
                    <small>{formatTimeStamp(flow.error?.timestamp)}</small>
                </div>
            </div>
        </section>
    )
}
