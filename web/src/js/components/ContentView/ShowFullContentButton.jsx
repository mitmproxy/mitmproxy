import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { render } from 'react-dom';
import Button from '../common/Button';
import { setShowFullContent } from '../../ducks/ui/flow'



ShowFullContentButton.propTypes = {
        setShowFullContent: PropTypes.func.isRequired,
        showFullContent: PropTypes.bool.isRequired
}

function ShowFullContentButton ( {setShowFullContent, showFullContent} ){

    return (
        !showFullContent && <Button isXs={true} onClick={() => setShowFullContent(true)} text="Show full content"/>
    )
}

export default connect(
    state => ({
        showFullContent: state.ui.flow.showFullContent
    }),
    {
        setShowFullContent
    }
)(ShowFullContentButton)

