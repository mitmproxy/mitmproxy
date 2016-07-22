import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'

import { RequestUtils, isValidHttpVersion, parseUrl } from '../../flow/utils.js'
import { formatTimeStamp } from '../../utils.js'
import ContentView from '../ContentView'
import ValidateEditor from '../ValueEditor/ValidateEditor'
import ValueEditor from '../ValueEditor/ValueEditor'
import FocusHelper from '../helpers/Focus'

import Headers from './Headers'
import { startEdit, updateEdit } from '../../ducks/ui/flow'
import ToggleEdit from './ToggleEdit'

class RequestLine extends Component {

    render() {
        const { flow, readonly, updateFLow, editType } = this.props
        return (
            <div className="first-line request-line">
                <div>
                    <ValueEditor
                        ref={FocusHelper('method' === editType)}
                        inline
                        content={flow.request.method}
                        readonly={readonly}
                        onDone={method => updateFlow({ request: { method } })}
                    />
                    &nbsp;
                    <ValidateEditor
                        ref={FocusHelper('url' === editType)}
                        inline
                        content={RequestUtils.pretty_url(flow.request)}
                        readonly={readonly}
                        onDone={url => updateFlow({ request: { path: '', ...parseUrl(url) } })}
                        isValid={url => !!parseUrl(url).host}
                    />
                    &nbsp;
                    <ValidateEditor
                        ref={FocusHelper('httpVersion' === editType)}
                        inline
                        content={flow.request.http_version}
                        readonly={readonly}
                        onDone={http_version => updateFlow({ request: { http_version } })}
                        isValid={isValidHttpVersion}
                    />
                </div>
            </div>
        )
    }
}

class ResponseLine extends Component {

    render() {
        const { flow, readonly, updateFlow, editType } = this.props
        return (
            <div className="first-line response-line">
                <ValidateEditor
                    ref={FocusHelper('httpVersion' === editType)}
                    inline
                    content={flow.response.http_version}
                    readonly={readonly}
                    onDone={nextVer => updateFlow({ response: { http_version: nextVer } })}
                    isValid={isValidHttpVersion}
                />
                &nbsp;
                <ValidateEditor
                    ref={FocusHelper('code' === editType)}
                    inline
                    content={flow.response.status_code + ''}
                    readonly={readonly}
                    onDone={code => updateFlow({ response: { code: parseInt(code) } })}
                    isValid={code => /^\d+$/.test(code)}
                />
                &nbsp;
                <ValueEditor
                    ref={FocusHelper('msg' === editType)}
                    inline
                    content={flow.response.reason}
                    readonly={readonly}
                    onDone={msg => updateFlow({ response: { msg } })}
                />
            </div>
        )
    }
}

const Message = connect(
    state => ({
        flow: state.ui.flow.modifiedFlow || state.flows.byId[state.flows.selected[0]],
        isEdit: !!state.ui.flow.modifiedFlow,
        editType: state.ui.focus.editType,
    }),
    {
        updateFlow: updateEdit,
    }
)

export class Request extends Component {
    render() {
        const { flow, isEdit, updateFlow, editType } = this.props

        return (
            <section className="request">
                <ToggleEdit/>
                <RequestLine
                    flow={flow}
                    readonly={!isEdit}
                    editType={editType}
                    updateFlow={updateFlow}
                />
                <Headers
                    message={flow.request}
                    readonly={!isEdit}
                    editType={editType}
                    onChange={headers => updateFlow({ request: { headers } })}
                />
                <hr/>
                <ContentView flow={flow} message={flow.request}/>
            </section>
        )
    }

}

Request = Message(Request)


export class Response extends Component {
    render() {
        const { flow, isEdit, updateFlow, editType } = this.props

        return (
            <section className="response">
                <ToggleEdit/>
                <ResponseLine
                    flow={flow}
                    readonly={!isEdit}
                    editType={editType}
                    updateFlow={updateFlow}/>
                <Headers
                    message={flow.response}
                    readonly={!isEdit}
                    editType={editType}
                    onChange={headers => updateFlow({ response: { headers } })}
                />
                <hr/>
                <ContentView flow={flow} message={flow.response}/>
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
