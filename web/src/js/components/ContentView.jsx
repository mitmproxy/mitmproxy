import React, { Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import * as ContentViews from './ContentView/ContentViews'
import * as MetaViews from './ContentView/MetaViews'
import ShowFullContentButton from './ContentView/ShowFullContentButton'


import { displayLarge, updateEdit } from '../ducks/ui/flow'

ContentView.propTypes = {
    // It may seem a bit weird at the first glance:
    // Every view takes the flow and the message as props, e.g.
    // <Auto flow={flow} message={flow.request}/>
    flow: PropTypes.object.isRequired,
    message: PropTypes.object.isRequired,
}

ContentView.isContentTooLarge = msg => msg.contentLength > 1024 * 1024 * (ContentViews.ViewImage.matches(msg) ? 10 : 0.2)

function ContentView(props) {
    const { flow, message, contentView, isDisplayLarge, displayLarge, onContentChange, readonly } = props

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
        </div>
    )
}

export default connect(
    state => ({
        contentView: state.ui.flow.contentView,
        isDisplayLarge: state.ui.flow.displayLarge,
    }),
    {
        displayLarge,
        updateEdit
    }
)(ContentView)
