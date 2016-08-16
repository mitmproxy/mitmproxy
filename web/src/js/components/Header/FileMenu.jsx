import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import classnames from 'classnames'
import FileChooser from '../common/FileChooser'
import * as flowsActions from '../../ducks/flows'



class FileMenu extends Component {

    static propTypes = {
        clearFlows: PropTypes.func.isRequired,
        loadFlows: PropTypes.func.isRequired,
        saveFlows: PropTypes.func.isRequired
    }

    constructor(props, context) {
        super(props, context)
        this.state = { show: false }

        this.close = this.close.bind(this)
        this.onFileClick = this.onFileClick.bind(this)
        this.onNewClick = this.onNewClick.bind(this)
        this.onOpenClick = this.onOpenClick.bind(this)
        this.onOpenFile = this.onOpenFile.bind(this)
        this.onSaveClick = this.onSaveClick.bind(this)
    }

    close() {
        this.setState({ show: false })
        document.removeEventListener('click', this.close)
    }

    onFileClick(e) {
        e.preventDefault()

        if (this.state.show) {
            return
        }

        document.addEventListener('click', this.close)
        this.setState({ show: true })
    }

    onNewClick(e) {
        e.preventDefault()
        if (confirm('Delete all flows?')) {
            this.props.clearFlows()
        }
    }

    onOpenClick(e) {
        e.preventDefault()
        this.fileInput.click()
    }

    onOpenFile(file) {
        this.props.loadFlows(file)
    }

    onSaveClick(e) {
        e.preventDefault()
        this.props.saveFlows()
    }

    render() {
        return (
            <div className={classnames('dropdown pull-left', { open: this.state.show })}>
                <a href="#" className="special" onClick={this.onFileClick}>mitmproxy</a>
                <ul className="dropdown-menu" role="menu">
                    <li>
                        <a href="#" onClick={this.onNewClick}>
                            <i className="fa fa-fw fa-file"></i>
                            New
                        </a>
                    </li>
                    <li>
                        <FileChooser
                            icon="fa-folder-open"
                            text="Open..."
                            onOpenFile={this.onOpenFile}
                        />
                    </li>
                    <li>
                        <a href="#" onClick={this.onSaveClick}>
                            <i className="fa fa-fw fa-floppy-o"></i>
                            Save...
                        </a>
                    </li>
                    <li role="presentation" className="divider"></li>
                    <li>
                        <a href="http://mitm.it/" target="_blank">
                            <i className="fa fa-fw fa-external-link"></i>
                            Install Certificates...
                        </a>
                    </li>
                </ul>
            </div>
        )
    }
}

export default connect(
    null,
    {
        clearFlows: flowsActions.clear,
        loadFlows: flowsActions.upload,
        saveFlows: flowsActions.download,
    }
)(FileMenu)
