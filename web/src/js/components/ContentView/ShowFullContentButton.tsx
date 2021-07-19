import React from 'react'
import Button from '../common/Button';
import { setShowFullContent } from '../../ducks/ui/flow'
import {useAppDispatch, useAppSelector} from "../../ducks";

export default function ShowFullContentButton() {
    const dispatch = useAppDispatch(),
    showFullContent = useAppSelector(state => state.ui.flow.showFullContent),
    visibleLines = useAppSelector(state => state.ui.flow.maxContentLines),
    contentLines = useAppSelector(state => state.ui.flow.content.length)

    return (
        !showFullContent ? (
            <div>
                <Button className="view-all-content-btn btn-xs" onClick={() => dispatch(setShowFullContent())}>
                    Show full content
                </Button>
                <span className="pull-right"> {visibleLines}/{contentLines} are visible &nbsp; </span>
            </div>
        ) : null
    )
}

