import React, { PropTypes } from 'react'
import ContentLoader from './ContentLoader'
import { MessageUtils } from '../../flow/utils.js'
import CodeEditor from '../common/CodeEditor'
import {formatSize} from '../../utils.js'



const views = [ViewAuto, ViewImage, ViewJSON, ViewRaw, ViewFile]

ViewImage.regex = /^image\/(png|jpe?g|gif|vnc.microsoft.icon|x-icon)$/i
ViewImage.matches = msg => ViewImage.regex.test(MessageUtils.getContentType(msg))

ViewImage.propTypes = {
    flow: PropTypes.object.isRequired,
    message: PropTypes.object.isRequired,
}

export function ViewImage({ flow, message }) {
    return (
        <div className="flowview-image">
            <img src={MessageUtils.getContentURL(flow, message)} alt="preview" className="img-thumbnail"/>
        </div>
    )
}

ViewRaw.textView = true
ViewRaw.matches = () => true
ViewRaw.input = {}

ViewRaw.propTypes = {
    content: React.PropTypes.string.isRequired,
}

export function ViewRaw({ content, update_content }) {
    return (
        <CodeEditor value={content} onSave={update_content}/>
    )
}

ViewJSON.textView = true
ViewJSON.regex = /^application\/json$/i
ViewJSON.matches = msg => ViewJSON.regex.test(MessageUtils.getContentType(msg))

ViewJSON.propTypes = {
    content: React.PropTypes.string.isRequired,
}

export function ViewJSON({ content }) {
    let json = content
    try {
        json = JSON.stringify(JSON.parse(content), null, 2);
    } catch (e) {
        // @noop
    }
    return <pre>{json}</pre>
}


ViewAuto.matches = () => false
ViewAuto.findView = msg => views.find(v => v.matches(msg)) || views[views.length - 1]

ViewAuto.propTypes = {
    message: React.PropTypes.object.isRequired,
    flow: React.PropTypes.object.isRequired,
}

export function ViewAuto({ message, flow, update_content }) {
    const View = ViewAuto.findView(message)
    if (View.textView) {
        return <ContentLoader message={message} flow={flow}><View update_content={update_content} content="" /></ContentLoader>
    } else {
        return <View message={message} flow={flow} />
    }
}

ViewFile.matches = () => false

ViewFile.propTypes = {
    message: React.PropTypes.object.isRequired,
    flow: React.PropTypes.object.isRequired,
}

export function ViewFile({ message, flow }) {
    return <div className="alert alert-info">
            {formatSize(message.contentLength)} content size.
        </div>
}

export default views
