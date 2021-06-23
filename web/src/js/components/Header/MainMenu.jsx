import React from "react"
import {connect} from "react-redux"
import FilterInput from "./FilterInput"
import {update as updateSettings} from "../../ducks/settings"
import * as flowsActions from "../../ducks/flows"
import {setFilter, setHighlight} from "../../ducks/flows"
import Button from "../common/Button"

MainMenu.title = "Start"

export default function MainMenu() {
    return (
        <div className="main-menu">
            <div className="menu-group">
                <div className="menu-content">
                    <FlowFilterInput/>
                    <HighlightInput/>
                </div>
                <div className="menu-legend">Find</div>
            </div>

            <div className="menu-group">
                <div className="menu-content">
                    <InterceptInput/>
                    <ResumeAll/>
                </div>
                <div className="menu-legend">Intercept</div>
            </div>
        </div>
    )
}

export function setIntercept(intercept) {
    return updateSettings({intercept})
}

const InterceptInput = connect(
    state => ({
        value: state.settings.intercept || '',
        placeholder: 'Intercept',
        type: 'pause',
        color: 'hsl(208, 56%, 53%)'
    }),
    {onChange: setIntercept}
)(FilterInput);

const FlowFilterInput = connect(
    state => ({
        value: state.flows.filter || '',
        placeholder: 'Search',
        type: 'search',
        color: 'black'
    }),
    {onChange: setFilter}
)(FilterInput);

const HighlightInput = connect(
    state => ({
        value: state.flows.highlight || '',
        placeholder: 'Highlight',
        type: 'tag',
        color: 'hsl(48, 100%, 50%)'
    }),
    {onChange: setHighlight}
)(FilterInput);

export function ResumeAll({resumeAll}) {
    return (
        <Button className="btn-sm" title="[a]ccept all"
                icon="fa-forward text-success" onClick={() => resumeAll()}>
            Resume All
        </Button>
    )
}

ResumeAll = connect(
    null,
    {resumeAll: flowsActions.resumeAll}
)(ResumeAll)
