import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import * as ContentViews from './ContentView/ContentViews'
import * as MetaViews from './ContentView/MetaViews'
import ViewSelector from './ContentView/ViewSelector'
import UploadContentButton from './ContentView/UploadContentButton'
import DownloadContentButton from './ContentView/DownloadContentButton'

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
    const { flow, message, contentView, selectView, displayLarge, setDisplayLarge, uploadContent, onContentChange, readonly } = props

    if (message.contentLength === 0) {
        return <MetaViews.ContentEmpty {...props}/>
    }

    if (message.contentLength === null) {
        return <MetaViews.ContentMissing {...props}/>
    }

    if (!displayLarge && ContentView.isContentTooLarge(message)) {
        return <MetaViews.ContentTooLarge {...props} onClick={displayLarge}/>
    }

    const View = ContentViews[contentView]
    return (
        <div>
            <View flow={flow} message={message} readonly={readonly} onChange={onContentChange}/>

            <div className="view-options text-center">
                <ViewSelector onSelectView={selectView} active={View} message={message}/>
                &nbsp;
                <DownloadContentButton flow={flow} message={message}/>
                &nbsp;
                <UploadContentButton uploadContent={uploadContent}/>
            </div>
        </div>
    )
}

export default connect(
    state => ({
        contentView: state.ui.flow.contentView,
        displayLarge: state.ui.flow.displayLarge,
    }),
    {
        selectView: setContentView,
        displayLarge,
        updateEdit
    }
)(ContentView)
