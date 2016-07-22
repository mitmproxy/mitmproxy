import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import FilterInput from './FilterInput'
import { setSelectedInput } from '../../ducks/ui/focus'
import { update as updateSettings } from '../../ducks/settings'
import { updateFilter, updateHighlight } from '../../ducks/flowView'

const InterceptInput = connect(
    state => ({
        value: state.settings.intercept || '',
        placeholder: 'Intercept',
        shouldFocus: state.ui.focus.selectedInput === 'intercept',
        type: 'pause',
        color: 'hsl(208, 56%, 53%)'
    }),
    { onChange: intercept => updateSettings({ intercept }) }
)(FilterInput)

const FlowFilterInput = connect(
    state => ({
        value: state.flowView.filter || '',
        placeholder: 'Search',
        shouldFocus: state.ui.focus.selectedInput === 'search',
        type: 'search',
        color: 'black'
    }),
    { onChange: updateFilter }
)(FilterInput)

const HighlightInput = connect(
    state => ({
        value: state.flowView.highlight || '',
        placeholder: 'Highlight',
        shouldFocus: state.ui.focus.selectedInput === 'highlight',
        type: 'tag',
        color: 'hsl(48, 100%, 50%)'
    }),
    { onChange: updateHighlight }
)(FilterInput)

MainMenu.title = 'Start'

class MainMenu extends Component {

    componentDidUpdate() {
        this.props.setSelectedInput(null)
    }

    render() {
        return (
            <div>
                <div className="menu-row">
                    <FlowFilterInput/>
                    <HighlightInput/>
                    <InterceptInput/>
                </div>
                <div className="clearfix"></div>
            </div>
        )
    }
}

export default connect(
    state => ({
        // noop
    }),
    {
        setSelectedInput,
    }
)(MainMenu)
