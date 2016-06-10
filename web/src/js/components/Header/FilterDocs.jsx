import React, { Component } from 'react'
import $ from 'jquery'

export default class FilterDocs extends Component {

    // @todo move to redux

    static xhr = null
    static doc = null

    constructor(props, context) {
        super(props, context)
        this.state = { doc: FilterDocs.doc }
    }

    componentWillMount() {
        if (!FilterDocs.xhr) {
            FilterDocs.xhr = $.getJSON('/filter-help')
            FilterDocs.xhr.fail(() => {
                FilterDocs.xhr = null
            })
        }
        if (!this.state.doc) {
            FilterDocs.xhr.done(doc => {
                FilterDocs.doc = doc
                this.setState({ doc })
            })
        }
    }

    render() {
        const { doc } = this.state
        return !doc ? (
            <i className="fa fa-spinner fa-spin"></i>
        ) : (
            <table className="table table-condensed">
                <tbody>
                    {doc.commands.map(cmd => (
                        <tr key={cmd[1]}>
                            <td>{cmd[0].replace(' ', '\u00a0')}</td>
                            <td>{cmd[1]}</td>
                        </tr>
                    ))}
                    <tr key="docs-link">
                        <td colSpan="2">
                            <a href="http://docs.mitmproxy.org/en/stable/features/filters.html"
                                target="_blank">
                                <i className="fa fa-external-link"></i>
                            &nbsp mitmproxy docs</a>
                        </td>
                    </tr>
                </tbody>
            </table>
        )
    }
}
