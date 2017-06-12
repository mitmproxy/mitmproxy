import React, { Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { render } from 'react-dom';
import Button from '../common/Button';
import { setShowFullContent } from '../../ducks/ui/flow'



ShowFullContentButton.propTypes = {
        setShowFullContent: PropTypes.func.isRequired,
        showFullContent: PropTypes.bool.isRequired
}

export function ShowFullContentButton ( {setShowFullContent, showFullContent, visibleLines, contentLines} ){

    return (
        !showFullContent &&
            <div>
                <Button className="view-all-content-btn btn-xs" onClick={() => setShowFullContent()}>
                    Show full content
                </Button>
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

