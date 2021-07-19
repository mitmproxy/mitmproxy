import React from 'react'
import _ from 'lodash'

import Nav from './FlowView/Nav'
import { ErrorView as Error, Request, Response } from './FlowView/Messages'
import Details from './FlowView/Details'

import { selectTab } from '../ducks/ui/flow'
import {useAppDispatch, useAppSelector} from "../ducks";

export const allTabs = { Request, Response, Error, Details }

export default function FlowView() {
    const dispatch = useAppDispatch(),
    flow = useAppSelector(state => state.flows.byId[state.flows.selected[0]])

    let tabName = useAppSelector(state => state.ui.flow.tab)

    // only display available tab names
    const tabs = ['request', 'response', 'error'].filter(k => flow[k])
    tabs.push("details")

    if (tabs.indexOf(tabName) < 0) {
        if (tabName === 'response' && flow.error) {
            tabName = 'error'
        } else if (tabName === 'error' && flow.response) {
            tabName = 'response'
        } else {
            tabName = tabs[0]
        }
    }

    const Tab = allTabs[_.capitalize(tabName)]

    return (
        <div className="flow-detail">
            <Nav
                tabs={tabs}
                active={tabName}
                onSelectTab={(tab: string) => dispatch(selectTab(tab))}
            />
            <Tab flow={flow}/>
        </div>
    )
}
