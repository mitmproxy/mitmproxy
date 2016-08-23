import React, { PropTypes, Component } from 'react'
import { connect } from 'react-redux'
import { setContentViewDescription, setContent } from '../../ducks/ui/flow'
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

class ViewServer extends Component {
    static propTypes  = {
        showFullContent: PropTypes.bool.isRequired,
        maxLines: PropTypes.number.isRequired,
        setContentViewDescription : PropTypes.func.isRequired,
        setContent: PropTypes.func.isRequired
    }

    componentWillMount(){
        this.setContentView(this.props)
    }

    componentWillReceiveProps(nextProps){
        if (nextProps.content != this.props.content) {
            this.setContentView(nextProps)
        }
    }

    setContentView(props){
        try {
            this.data = JSON.parse(props.content)
        }catch(err) {
            this.data = {lines: [], description: err.message}
        }

        props.setContentViewDescription(props.contentView != this.data.description ? this.data.description : '')
        props.setContent(this.data.lines)
    }

    render() {
        const {content, contentView, message, maxLines} = this.props
        let lines = this.props.showFullContent ? this.data.lines : this.data.lines.slice(0, maxLines)
        return (
            <div>
                <pre>
                    {lines.map((line, i) =>
                        <div key={`line${i}`}>
                            {line.map((element, j) => {
                                let [style, text] = element
                                return (
                                    <span key={`tuple${j}`} className={style}>
                                        {text}
                                    </span>
                                )
                            })}
                        </div>
                    )}
                </pre>
                {ViewImage.matches(message) &&
                <ViewImage {...this.props} />
                }
            </div>
        )
    }

}

ViewServer = connect(
    state => ({
        showFullContent: state.ui.flow.showFullContent,
        maxLines: state.ui.flow.maxContentLines
    }),
    {
        setContentViewDescription,
        setContent
    }
)(ContentLoader(ViewServer))

export { Edit, ViewServer, ViewImage }
