import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import * as ContentViews from './ContentView/ContentViews'
import * as MetaViews from './ContentView/MetaViews'
import ViewSelector from './ContentView/ViewSelector'
import UploadContentButton from './ContentView/UploadContentButton'
import DownloadContentButton from './ContentView/DownloadContentButton'
import ShowFullContentButton from './ContentView/ShowFullContentButton'

import { setContentView, displayLarge, updateEdit } from '../ducks/ui/flow'

ContentView.propTypes = {
    // It may seem a bit weird at the first glance:
    // Every view takes the flow and the message as props, e.g.
    // <Auto flow={flow} message={flow.request}/>
    flow: React.PropTypes.object.isRequired,
    message: React.PropTypes.object.isRequired,
}

ContentView.isContentTooLarge = msg => msg.contentLength > 1024 * 1024 * (ContentViews.ViewImage.matches(msg) ? 10 : 0.2)

function ContentView(props) {
    const { flow, message, contentView, isDisplayLarge, displayLarge, uploadContent, onContentChange, readonly, contentViewDescription } = props

    if (message.contentLength === 0 && readonly) {
        return <MetaViews.ContentEmpty {...props}/>
    }

    if (message.contentLength === null && readonly) {
        return <MetaViews.ContentMissing {...props}/>
    }

    if (!isDisplayLarge && ContentView.isContentTooLarge(message)) {
        return <MetaViews.ContentTooLarge {...props} onClick={displayLarge}/>
    }

    const View = ContentViews[contentView] || ContentViews['ViewServer']
    return (
        <div className="contentview">
            <View flow={flow} message={message} contentView={contentView} readonly={readonly} onChange={onContentChange}/>
            <ShowFullContentButton/>
            <div className="view-options footer navbar-fixed-bottom">
                <ViewSelector message={message}/>
                &nbsp;
                <DownloadContentButton flow={flow} message={message}/>
                &nbsp;
                <UploadContentButton uploadContent={uploadContent}/>
                &nbsp;
                <span>{contentViewDescription}</span>
            </div>
        </div>
    )
}

export default connect(
    state => ({
        contentView: state.ui.flow.contentView,
        isDisplayLarge: state.ui.flow.displayLarge,
        contentViewDescription: state.ui.flow.viewDescription
    }),
    {
        displayLarge,
        updateEdit
    }
)(ContentView)
