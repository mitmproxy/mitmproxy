import React, { Component } from "react"
import PropTypes from 'prop-types'
import { connect } from "react-redux"
import FilterInput from "./FilterInput"
import { update as updateSettings } from "../../ducks/settings"
import { setFilter, setHighlight } from "../../ducks/flows"
import * as flowsActions from "../../ducks/flows"
import Button from "../common/Button"

MainMenu.title = "Start"

export default function MainMenu() {
    return (
        <div className="menu-main">
            <div className="menu-group">
                <div className="menu-content">
                    <FlowFilterInput/>
                    <HighlightInput/>
                </div>
                <div className="menu-legend">search/filter</div>
            </div>

            <div className="menu-group">
                <div className="menu-content">
                    <InterceptInput/>
                    <ResumeAll/>
                </div>
                <div className="menu-legend">intercept</div>
            </div>
        </div>
    )
}

export function setIntercept(intercept) {
    updateSettings({ intercept })
}

const InterceptInput = connect(
    state => ({
        value: state.settings.intercept || '',
        placeholder: 'Intercept',
        type: 'pause',
        color: 'hsl(208, 56%, 53%)'
    }),
    { onChange: setIntercept }
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

export function ResumeAll({resumeAll}) {
    return (
        <Button className="resume-all" title="[a]ccept all"
                icon="fa-forward text-success" onClick={() => resumeAll()}>
                    Resume All
        </Button>
    )
}

ResumeAll = connect(
    null,
    { resumeAll: flowsActions.resumeAll }
)(ResumeAll)