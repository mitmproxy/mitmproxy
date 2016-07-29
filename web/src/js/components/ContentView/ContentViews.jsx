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

Edit.propTypes = {
    content: React.PropTypes.string.isRequired,
}

function Edit({ content, onChange }) {
    return <CodeEditor content={content} onChange={onChange}/>
}
Edit = ContentLoader(Edit)


function ViewServer(props){
    const {content, contentView, message} = props
    let data = JSON.parse(content)

    return <div>
            {contentView != data.description &&
                <div className="alert alert-warning">{data.description}</div>
            }
            <pre>
                {data.lines.map((line, i) =>
                    <div key={`line${i}`}>
                        {line.map((tuple, j) =>
                            <span key={`tuple${j}`} className={tuple[0]}>
                                {tuple[1]}
                            </span>
                        )}
                    </div>
                )}
            </pre>
            {ViewImage.matches(message) &&
                <ViewImage {...props} />
            }
        </div>
}

ViewServer = ContentLoader(ViewServer)

export { Edit, ViewServer, ViewImage }
