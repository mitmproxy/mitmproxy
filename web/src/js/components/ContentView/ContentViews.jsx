import React, { PropTypes } from 'react'
import ContentLoader from './ContentLoader'
import { MessageUtils } from '../../flow/utils'
import CodeEditor from './CodeEditor'


const isImage = /^image\/(png|jpe?g|gif|vnc.microsoft.icon|x-icon)$/i
ViewImage.matches = msg => isImage.test(MessageUtils.getContentType(msg))
ViewImage.propTypes = {
    flow: PropTypes.object.isRequired,
    message: PropTypes.object.isRequired,
}
function ViewImage({ flow, message }) {
    return (
        <div className="flowview-image">
            <img src={MessageUtils.getContentURL(flow, message)} alt="preview" className="img-thumbnail"/>
        </div>
    )
}


ViewRaw.matches = () => true
ViewRaw.propTypes = {
    content: React.PropTypes.string.isRequired,
}
function ViewRaw({ content, readonly, onChange }) {
    return readonly ? <pre>{content}</pre> : <CodeEditor content={content} onChange={onChange}/>
}
ViewRaw = ContentLoader(ViewRaw)


const isJSON = /^application\/json$/i
ViewJSON.matches = msg => isJSON.test(MessageUtils.getContentType(msg))
ViewJSON.propTypes = {
    content: React.PropTypes.string.isRequired,
}
function ViewJSON({ content }) {
    let json = content
    try {
        json = JSON.stringify(JSON.parse(content), null, 2);
    } catch (e) {
        // @noop
    }
    return <pre>{json}</pre>
}
ViewJSON = ContentLoader(ViewJSON)


ViewAuto.matches = () => false
ViewAuto.findView = msg => [ViewImage, ViewJSON, ViewRaw].find(v => v.matches(msg)) || ViewRaw
ViewAuto.propTypes = {
    message: React.PropTypes.object.isRequired,
    flow: React.PropTypes.object.isRequired,
}
function ViewAuto({ message, flow, readonly, onChange }) {
    const View = ViewAuto.findView(message)
    return <View message={message} flow={flow} readonly={readonly} onChange={onChange}/>
}

export { ViewImage, ViewRaw, ViewAuto, ViewJSON }
