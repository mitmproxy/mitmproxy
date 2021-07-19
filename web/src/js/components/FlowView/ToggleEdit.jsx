import React from 'react'
import {useAppDispatch, useAppSelector} from "../../ducks";
import { startEdit, stopEdit } from '../../ducks/ui/flow'


export default function ToggleEdit() {
    const dispatch = useAppDispatch(),
    isEdit = useAppSelector(state => !!state.ui.flow.modifiedFlow),
    modifiedFlow = useAppSelector(state => state.ui.flow.modifiedFlow|| state.flows.byId[state.flows.selected[0]]),
    flow = useAppSelector(state => state.flows.byId[state.flows.selected[0]])

    return (
        <div className="edit-flow-container">
            {isEdit ?
                <a className="edit-flow" title="Finish Edit" onClick={() => dispatch(stopEdit(flow, modifiedFlow))}>
                    <i className="fa fa-check"/>
                </a>
                :
                <a className="edit-flow" title="Edit Flow" onClick={() => dispatch(startEdit(flow))}>
                    <i className="fa fa-pencil"/>
                </a>
            }
        </div>
    )
}
