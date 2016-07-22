import React, { Component, PropTypes } from 'react'
import ReactDOM from 'react-dom'
import ValueEditor from '../ValueEditor/ValueEditor'
import { Key } from '../../utils'
import FocusHelper from '../helpers/Focus'

class HeaderEditor extends Component {

    constructor(props, context) {
        super(props, context)
        this.onKeyDown = this.onKeyDown.bind(this)
    }

    render() {
        return <ValueEditor {...this.props} inline onKeyDown={this.onKeyDown} />
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

    static propTypes = {
        onChange: PropTypes.func.isRequired,
        message: PropTypes.object.isRequired,
    }

    onChange(row, col, val) {
        const nextHeaders = _.cloneDeep(this.props.message.headers)

        nextHeaders[row][col] = val

        if (nextHeaders[row][0] || nextHeaders[row][1]) {
            this.props.onChange(nextHeaders)
            return
        }

        // do not delete last row
        if (nextHeaders.length === 1) {
            nextHeaders[0][0] = 'Name'
            nextHeaders[0][1] = 'Value'
            this.props.onChange(nextHeaders)
            return
        }

        nextHeaders.splice(row, 1)

        // manually move selection target if this has been the last row.
        if (row === nextHeaders.length) {
            this.setState({ nextSel: 2 * row - 1 })
        }

        this.props.onChange(nextHeaders)
    }

    onTab(row, col, e) {
        const headers = this.props.message.headers

        if (col === 0) {
            this.setState({ nextSel: 2 * row + 1 })
            return
        }
        if (row !== headers.length - 1) {
            this.setState({ nextSel: 2 * row + 2 })
            return
        }

        e.preventDefault()

        const nextHeaders = _.clone(this.props.message.headers)

        nextHeaders.push(['Name', 'Value'])

        this.props.onChange(nextHeaders)
        this.setState({ nextSel: 2 * row + 2 })
    }

    componentDidUpdate() {
        this.setState({ nextSel: null })
    }

    onRemove(row, col, e) {
        if (col === 1) {
            e.preventDefault()
            this.setState({ nextSel: 2 * row })
        } else if (row > 0) {
            e.preventDefault()
            this.setState({ nextSel: 2 * row - 1 })
        }
    }

    render() {
        const { message, readonly, editType } = this.props
        const { nextSel } = this.state

        return (
            <table className="header-table">
                <tbody>
                    {message.headers.map((header, i) => (
                        <tr key={i}>
                            <td className="header-name">
                                <HeaderEditor
                                    ref={FocusHelper(2 * i === nextSel && 'headers' === editType)}
                                    content={header[0]}
                                    readonly={readonly}
                                    onDone={val => this.onChange(i, 0, val)}
                                    onRemove={event => this.onRemove(i, 0, event)}
                                    onTab={event => this.onTab(i, 0, event)}
                                />:
                            </td>
                            <td className="header-value">
                                <HeaderEditor
                                    ref={FocusHelper(2 * i + 1 === nextSel && 'headers' === editType)}
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
        )
    }
}
