import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { MessageUtils } from '../flow/utils.js'
import * as ContentViews from './ContentView/ContentViews'
import * as MetaViews from './ContentView/MetaViews'
import ContentLoader from './ContentView/ContentLoader'
import ViewSelector from './ContentView/ViewSelector'
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
            {View.textView ? (
                <ContentLoader flow={flow} message={message}>
                    <View readonly={readonly} onChange={onContentChange} content="" />
                </ContentLoader>
            ) : (
                <View flow={flow} readonly={readonly} message={message} />
            )}
            <div className="view-options text-center">
                <ViewSelector onSelectView={selectView} active={View} message={message}/>
                &nbsp;
                <a className="btn btn-default btn-xs"
                   href={MessageUtils.getContentURL(flow, message)}
                   title="Download the content of the flow.">
                    <i className="fa fa-download"/>
                </a>
                &nbsp;
                <a  className="btn btn-default btn-xs"
                    onClick={() => ContentView.fileInput.click()}
                    title="Upload a file to replace the content."
                >
                    <i className="fa fa-upload"/>
                </a>
                <input
                    ref={ref => ContentView.fileInput = ref}
                    className="hidden"
                    type="file"
                    onChange={e => {if(e.target.files.length > 0) uploadContent(e.target.files[0])}}
                />
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
        updateEdit,
    }
)(ContentView)
