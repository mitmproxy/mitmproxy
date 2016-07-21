import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import FilterInput from './FilterInput'
import { update as updateSettings } from '../../ducks/settings'
import { updateFilter, updateHighlight } from '../../ducks/flowView'

MainMenu.title = "Start"

export default function MainMenu() {
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

const InterceptInput = connect(
    state => ({
        value: state.settings.intercept || '',
        placeholder: 'Intercept',
        type: 'pause',
        color: 'hsl(208, 56%, 53%)'
    }),
    { onChange: intercept => updateSettings({ intercept }) }
)(FilterInput);

const FlowFilterInput = connect(
    state => ({
        value: state.flowView.filter || '',
        placeholder: 'Search',
        type: 'search',
        color: 'black'
    }),
    { onChange: updateFilter }
)(FilterInput);

const HighlightInput = connect(
    state => ({
        value: state.flowView.highlight || '',
        placeholder: 'Highlight',
        type: 'tag',
        color: 'hsl(48, 100%, 50%)'
    }),
    { onChange: updateHighlight }
)(FilterInput);
