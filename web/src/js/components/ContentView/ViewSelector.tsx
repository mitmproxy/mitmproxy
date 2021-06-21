import React from 'react'
import {setContentView} from '../../ducks/ui/flow';
import Dropdown, {MenuItem} from '../common/Dropdown'
import {useAppDispatch, useAppSelector} from "../../ducks";


export default React.memo(function ViewSelector() {
    const dispatch = useAppDispatch(),
        contentViews = useAppSelector(state => state.conf.contentViews || []),
        activeView = useAppSelector(state => state.ui.flow.contentView);

    let inner = <span><b>View:</b> {activeView.toLowerCase()} <span className="caret"/></span>

    return (
        <Dropdown
            text={inner}
            className="btn btn-default btn-xs pull-left"
            options={{placement: "top-start"}}>
            {contentViews.map(name =>
                <MenuItem key={name} onClick={() => dispatch(setContentView(name))}>
                    {name.toLowerCase().replace('_', ' ')}
                </MenuItem>
            )}
        </Dropdown>
    )
});
