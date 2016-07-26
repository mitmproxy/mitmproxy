import React, { Component, PropTypes } from 'react'
import { MessageUtils } from '../../flow/utils.js'

export default View => class extends React.Component {

    static displayName = View.displayName || View.name
    static matches = View.matches

    static propTypes = {
        ...View.propTypes,
        content: PropTypes.string,  // mark as non-required
        flow: PropTypes.object.isRequired,
        message: PropTypes.object.isRequired,
    }

    constructor(props) {
        super(props)
        this.state = {
            content: undefined,
            request: undefined,
        }
    }

    componentWillMount() {
        this.startRequest(this.props)
    }

    componentWillReceiveProps(nextProps) {
        if (nextProps.message.contentHash !== this.props.message.contentHash) {
            this.startRequest(nextProps)
        }
    }

    componentWillUnmount() {
        if (this.state.request) {
            this.state.request.abort()
        }
    }

    startRequest(props) {
        if (this.state.request) {
            this.state.request.abort()
        }
        if(props.message.contentLength === 0 || props.message.contentLength === null){
            return this.setState({request: undefined, content: ""})
        }

        let requestUrl = MessageUtils.getContentURL(props.flow, props.message)

        // We use XMLHttpRequest instead of fetch() because fetch() is not (yet) abortable.
        let request = new XMLHttpRequest();
        request.addEventListener("load", this.requestComplete.bind(this, request));
        request.addEventListener("error", this.requestFailed.bind(this, request));
        request.open("GET", requestUrl);
        request.send();
        this.setState({ request, content: undefined })
    }

    requestComplete(request, e) {
        if (request !== this.state.request) {
            return // Stale request
        }
        this.setState({
            content: request.responseText,
            request: undefined
        })
    }

    requestFailed(request, e) {
        if (request !== this.state.request) {
            return // Stale request
        }
        console.error(e)
        // FIXME: Better error handling
        this.setState({
            content: "Error getting content.",
            request: undefined
        })
    }

    render() {
        return this.state.content !== undefined ? (
            <View content={this.state.content} {...this.props}/>
        ) : (
            <div className="text-center">
                <i className="fa fa-spinner fa-spin"></i>
            </div>
        )
    }
};
