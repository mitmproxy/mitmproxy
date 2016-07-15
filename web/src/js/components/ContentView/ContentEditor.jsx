import React, { Component, PropTypes } from 'react'
import CodeEditor from '../common/CodeEditor'

export default class ContentEditor extends Component {

    static propTypes = {
        content: PropTypes.string.isRequired,
        onSave: PropTypes.func.isRequired,
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
                    <a  className="edit-flow" onClick={this.props.onOpen}>
                        <i className="fa fa-pencil"/>
                    </a> :
                    <a className="edit-flow"  onClick={() => this.props.onSave(this.state.content)}>
                        <i className="fa fa-check"/>
                    </a>
                }
                {!this.props.isClosed &&
                    <CodeEditor value={this.state.content} onChange={content => this.setState({content: content})}/>
                }
            </div>

        )
    }
}
