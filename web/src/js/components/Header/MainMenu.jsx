import React, { Component, PropTypes } from "react"
import { connect } from "react-redux"
import FilterInput from "./FilterInput"
import { update as updateSettings } from "../../ducks/settings"
import { setFilter, setHighlight } from "../../ducks/flows"

MainMenu.title = "Start"

export default function MainMenu() {
    return (
        <div className="menu-main">
            <FlowFilterInput/>
            <HighlightInput/>
            <InterceptInput/>
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
        value: state.flows.filter || '',
        placeholder: 'Search',
        type: 'search',
        color: 'black'
    }),
    { onChange: setFilter }
)(FilterInput);

const HighlightInput = connect(
    state => ({
        value: state.flows.highlight || '',
        placeholder: 'Highlight',
        type: 'tag',
        color: 'hsl(48, 100%, 50%)'
    }),
    { onChange: setHighlight }
)(FilterInput);
