import React, { Component, PropTypes } from 'react'
import { MessageUtils } from '../../flow/utils.js'
// This is the only place where we use jQuery.
// Remove when possible.
import $ from "jquery"

export default class ContentLoader extends Component {

    static propTypes = {
        flow: PropTypes.object.isRequired,
        message: PropTypes.object.isRequired,
    }

    constructor(props, context) {
        super(props, context)
        this.state = { content: null, request: null }
    }

    requestContent(nextProps) {
        if (this.state.request) {
            this.state.request.abort()
        }

        const requestUrl = MessageUtils.getContentURL(nextProps.flow, nextProps.message)
        const request = $.get(requestUrl)

        this.setState({ content: null, request })

        request
            .done(content => {
                this.setState({ content })
            })
            .fail((xhr, textStatus, errorThrown) => {
                if (textStatus === 'abort') {
                    return
                }
                this.setState({ content: `AJAX Error: ${textStatus}\r\n${errorThrown}` })
            })
            .always(() => {
                this.setState({ request: null })
            })
    }

    componentWillMount() {
        this.requestContent(this.props)
    }

    componentWillReceiveProps(nextProps) {
        let reload = nextProps.message !== this.props.message
        let isUserEdit = !nextProps.readonly && nextProps.message.content

        if (isUserEdit)
            this.setState({content: nextProps.message.content})
        else if(reload)
            this.requestContent(nextProps)
    }

    componentWillUnmount() {
        if (this.state.request) {
            this.state.request.abort()
        }
    }

    render() {
        return this.state.content ? (
            React.cloneElement(this.props.children, {
                content: this.state.content
            })
        ) : (
            <div className="text-center">
                <i className="fa fa-spinner fa-spin"></i>
            </div>
        )
    }
}
