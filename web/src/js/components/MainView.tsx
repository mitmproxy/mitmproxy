import * as React from "react"
import Splitter from './common/Splitter'
import FlowTable from './FlowTable'
import FlowView from './FlowView'
import {useAppSelector} from "../ducks";

export default function MainView() {
    const hasSelection = useAppSelector(state => !!state.flows.byId[state.flows.selected[0]])
    return (
        <div className="main-view">
            <FlowTable/>
            {hasSelection && <Splitter key="splitter"/>}
            {hasSelection && <FlowView key="flowDetails"/>}
        </div>
    )
}
