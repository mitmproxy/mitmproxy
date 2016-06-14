import React, { Component } from 'react'
import classnames from 'classnames'
import { FlowActions } from '../../actions.js'

export default class FileMenu extends Component {

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
            FlowActions.clear()
        }
    }

    onOpenClick(e) {
        e.preventDefault()
        this.fileInput.click()
    }

    onOpenFile(e) {
        e.preventDefault()
        if (e.target.files.length > 0) {
            FlowActions.upload(e.target.files[0])
            this.fileInput.value = ''
        }
    }

    onSaveClick(e) {
        e.preventDefault()
        FlowActions.download()
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
                        <a href="#" onClick={this.onOpenClick}>
                            <i className="fa fa-fw fa-folder-open"></i>
                            Open...
                        </a>
                        <input
                            ref={ref => this.fileInput = ref}
                            className="hidden"
                            type="file"
                            onChange={this.onOpenFile}
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
