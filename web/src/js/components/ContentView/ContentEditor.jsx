import React, { Component, PropTypes } from 'react'
import CodeEditor from '../common/CodeEditor'

export default class ContentEditor extends Component {

    static propTypes = {
        content: PropTypes.string.isRequired,
        onSave: PropTypes.func.isRequired,
        onClose: PropTypes.func.isRequired,
        onOpen: PropTypes.func.isRequired,
        isClosed: PropTypes.bool.isRequired
    }

    constructor(props){
        super(props)
        this.state = {content: this.props.content}
    }

    render() {
        return (
            <div>
                {this.props.isClosed ?
                    <a  className="btn btn-default btn-xs pull-right" onClick={this.props.onOpen}>
                        <i className="fa fa-pencil-square-o"/>
                    </a> :
                    <span>
                        <a className="btn btn-default btn-xs pull-right" onClick={this.props.onClose}>
                            <i className="fa fa-times"/>
                        </a>
                        <a className="btn btn-default btn-xs pull-right"  onClick={() => this.props.onSave(this.state.content)}>
                            <i className="fa fa-floppy-o"/>
                        </a>
                    </span>
                }
                {!this.props.isClosed &&
                    <CodeEditor value={this.state.content} onChange={content => this.setState({content: content})}/>
                }
            </div>

        )
    }
}
