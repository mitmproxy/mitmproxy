import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { render } from 'react-dom';
import Button from '../common/Button';
import { setShowFullContent } from '../../ducks/ui/flow'



ShowFullContentButton.propTypes = {
        setShowFullContent: PropTypes.func.isRequired,
        showFullContent: PropTypes.bool.isRequired
}

function ShowFullContentButton ( {setShowFullContent, showFullContent, visibleLines, contentLines} ){

    return (
        !showFullContent &&
            <div>
                <Button className="view-all-content-btn btn-xs" onClick={() => setShowFullContent()} text="Show full content"/>
                <span className="pull-right"> {visibleLines}/{contentLines} are visible &nbsp; </span>
            </div>
    )
}

export default connect(
    state => ({
        showFullContent: state.ui.flow.showFullContent,
        visibleLines: state.ui.flow.maxContentLines,
        contentLines: state.ui.flow.content.length

    }),
    {
        setShowFullContent
    }
)(ShowFullContentButton)

