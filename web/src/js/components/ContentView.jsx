import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { MessageUtils } from '../flow/utils.js'
import * as ContentViews from './ContentView/ContentViews'
import * as MetaViews from './ContentView/MetaViews'
import ContentLoader from './ContentView/ContentLoader'
import ViewSelector from './ContentView/ViewSelector'
import { setContentView, setDisplayLarge } from '../ducks/ui'

ContentView.propTypes = {
    // It may seem a bit weird at the first glance:
    // Every view takes the flow and the message as props, e.g.
    // <Auto flow={flow} message={flow.request}/>
    flow: React.PropTypes.object.isRequired,
    message: React.PropTypes.object.isRequired,
}

ContentView.isContentTooLarge = msg => msg.contentLength > 1024 * 1024 * (ContentViews.ViewImage.matches(msg) ? 10 : 0.2)

function ContentView({ flow, message, contentView, selectView, displayLarge }) {

    if (message.contentLength === 0) {
        return <MetaViews.ContentEmpty {...this.props}/>
    }

    if (message.contentLength === null) {
        return <MetaViews.ContentMissing {...this.props}/>
    }

    if (!displayLarge && ContentView.isContentTooLarge(message)) {
        return <MetaViews.ContentTooLarge {...this.props} onClick={() => this.props.setDisplayLarge(true)}/>
    }

    const View = ContentViews[contentView]

    return (
        <div>
            {View.textView ? (
                <ContentLoader flow={flow} message={message}>
                    <View content="" />
                </ContentLoader>
            ) : (
                <View flow={flow} message={message} />
            )}
            <div className="view-options text-center">
                <ViewSelector onSelectView={selectView} active={View} message={message}/>
                &nbsp;
                <a className="btn btn-default btn-xs" href={MessageUtils.getContentURL(flow, message)}>
                    <i className="fa fa-download"/>
                </a>
            </div>
        </div>
    )
}

export default connect(
    state => ({
        contentView: state.ui.contentView,
        displayLarge: state.ui.displayLarge,
    }),
    {
        selectView: setContentView,
        setDisplayLarge,
    }
)(ContentView)
