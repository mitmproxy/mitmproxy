import React, { Component } from 'react'
import PropTypes from 'prop-types'
import ReactDOM from 'react-dom'
import ValueEditor from '../ValueEditor/ValueEditor'
import CodeEditor from '../ContentView/CodeEditor'
import Button from "../common/Button"
import { Key } from '../../utils'
import { MessageUtils } from '../../flow/utils.js'

function RawHeaderEditor({content, onChange}) {
    return <CodeEditor content={ MessageUtils.reconstructRawHeader(content) } onChange={ content => {
        let headers = MessageUtils.splitRawHeaderIntoArray(content.trim());
        onChange(headers);
    }}/>
}

export class HeaderEditor extends Component {

    constructor(props) {
        super(props)
        this.onKeyDown = this.onKeyDown.bind(this)
    }

    render() {
        let { onTab, ...props } = this.props
        return <ValueEditor
            {...props}
            onKeyDown={this.onKeyDown}
        />
    }

    focus() {
        ReactDOM.findDOMNode(this).focus()
    }

    onKeyDown(e) {
        switch (e.keyCode) {
            case Key.BACKSPACE:
                var s = window.getSelection().getRangeAt(0)
                if (s.startOffset === 0 && s.endOffset === 0) {
                    this.props.onRemove(e)
                }
                break
            case Key.ENTER:
            case Key.TAB:
                if (!e.shiftKey) {
                    this.props.onTab(e)
                }
                break
        }
    }
}

export default class Headers extends Component {
    constructor(props) {
        super(props)
        this.state = {raw_edit: false}
    }

    static propTypes = {
        onChange: PropTypes.func.isRequired,
        message: PropTypes.object.isRequired,
        type: PropTypes.string.isRequired,
    }

    static defaultProps = {
        type: 'headers',
    }

    onChange(row, col, val) {
        const nextHeaders = _.cloneDeep(this.props.message[this.props.type])

        nextHeaders[row][col] = val

        if (!nextHeaders[row][0] && !nextHeaders[row][1]) {
            // do not delete last row
            if (nextHeaders.length === 1) {
                nextHeaders[0][0] = 'Name'
                nextHeaders[0][1] = 'Value'
            } else {
                nextHeaders.splice(row, 1)
                // manually move selection target if this has been the last row.
                if (row === nextHeaders.length) {
                    this._nextSel = `${row - 1}-value`
                }
            }
        }

        this.props.onChange(nextHeaders)
    }

    edit() {
        this.refs['0-key'].focus()
    }

    onTab(row, col, e) {
        const headers = this.props.message[this.props.type]

        if (col === 0) {
            this._nextSel = `${row}-value`
            return
        }
        if (row !== headers.length - 1) {
            this._nextSel = `${row + 1}-key`
            return
        }

        e.preventDefault()

        const nextHeaders = _.cloneDeep(this.props.message[this.props.type])
        nextHeaders.push(['Name', 'Value'])
        this.props.onChange(nextHeaders)
        this._nextSel = `${row + 1}-key`
    }

    componentDidUpdate() {
        if (this._nextSel && this.refs[this._nextSel]) {
            this.refs[this._nextSel].focus()
            this._nextSel = undefined
        }
    }

    onRemove(row, col, e) {
        if (col === 1) {
            e.preventDefault()
            this.refs[`${row}-key`].focus()
        } else if (row > 0) {
            e.preventDefault()
            this.refs[`${row - 1}-value`].focus()
        }
    }

    render() {
        const { message, readonly } = this.props
        if (message[this.props.type]) {
            if (!readonly && this.state.raw_edit) {
                return (
                    <div>
                        <RawHeaderEditor content={message[this.props.type]} onChange={ this.props.onChange }/>
                        <Button title="change mode"
                            onClick={() => this.setState({raw_edit: !this.state.raw_edit})}>
                                switch mode
                        </Button>
                    </div>
                )
            }
            return (
                <div>
                    <table className="header-table">
                        <tbody>
                        {message[this.props.type].map((header, i) => (
                            <tr key={i}>
                                <td className="header-name">
                                    <HeaderEditor
                                        ref={`${i}-key`}
                                        content={header[0]}
                                        readonly={readonly}
                                        onDone={val => this.onChange(i, 0, val)}
                                        onRemove={event => this.onRemove(i, 0, event)}
                                        onTab={event => this.onTab(i, 0, event)}
                                    />
                                    <span className="header-colon">:</span>
                                </td>
                                <td className="header-value">
                                    <HeaderEditor
                                        ref={`${i}-value`}
                                        content={header[1]}
                                        readonly={readonly}
                                        onDone={val => this.onChange(i, 1, val)}
                                        onRemove={event => this.onRemove(i, 1, event)}
                                        onTab={event => this.onTab(i, 1, event)}
                                    />
                                </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    {readonly ? null : <Button title="change mode"
                            onClick={() => this.setState({raw_edit: !this.state.raw_edit})}>
                                switch mode
                    </Button>}
                </div>
            )
        } else {
            return (
                <table className="header-table">
                    <tbody>
                    </tbody>
                </table>
            )
        }
    }
}
