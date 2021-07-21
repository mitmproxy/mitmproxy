import React from 'react'
import { MessageUtils } from '../../flow/utils'
import { Flow, HTTPMessage } from '../../flow'

type ContentLoaderProps = {
    content: string,
    contentView: object,
    flow: Flow,
    message: HTTPMessage,
}

type ContentLoaderStates = {
    content: string | undefined,
    request: { abort: () => void }| undefined,
}

export default function withContentLoader(View) {

    return class extends React.Component<ContentLoaderProps, ContentLoaderStates> {
        static displayName: string = View.displayName || View.name
        static matches: (message: any) => boolean = View.matches

        constructor(props) {
            super(props)
            this.state = {
                content: undefined,
                request: undefined,
            }
        }

        componentDidMount() {
            this.updateContent(this.props)
        }

        UNSAFE_componentWillReceiveProps(nextProps) {
            if (
                nextProps.message.content !== this.props.message.content ||
                nextProps.message.contentHash !== this.props.message.contentHash ||
                nextProps.contentView !== this.props.contentView
            ) {
                this.updateContent(nextProps)
            }
        }

        componentWillUnmount() {
            if (this.state.request) {
                this.state.request.abort()
            }
        }

        updateContent(props) {
            if (this.state.request) {
                this.state.request.abort()
            }
            // We have a few special cases where we do not need to make an HTTP request.
            if (props.message.content !== undefined) {
                return this.setState({request: undefined, content: props.message.content})
            }
            if (props.message.contentLength === 0) {
                return this.setState({request: undefined, content: ""})
            }

            let requestUrl = MessageUtils.getContentURL(props.flow, props.message, props.contentView)

            // We use XMLHttpRequest instead of fetch() because fetch() is not (yet) abortable.
            let request = new XMLHttpRequest();
            request.addEventListener("load", this.requestComplete.bind(this, request));
            request.addEventListener("error", this.requestFailed.bind(this, request));
            request.open("GET", requestUrl);
            request.send();
            this.setState({request, content: undefined})
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
    }
};
