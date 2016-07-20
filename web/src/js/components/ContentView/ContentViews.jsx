import React, { PropTypes } from 'react'
import ContentLoader from './ContentLoader'
import { MessageUtils } from '../../flow/utils.js'


const views = [ViewAuto, ViewImage, ViewJSON, ViewRaw]

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

ViewRaw.propTypes = {
    content: React.PropTypes.string.isRequired,
}

export function ViewRaw({ content }) {
    return <pre>{content}</pre>
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

export function ViewAuto({ message, flow }) {
    const View = ViewAuto.findView(message)
    if (View.textView) {
        return <ContentLoader message={message} flow={flow}><View content="" /></ContentLoader>
    } else {
        return <View message={message} flow={flow} />
    }
}

export default views
