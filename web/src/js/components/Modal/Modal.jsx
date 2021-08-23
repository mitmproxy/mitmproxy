import * as React from "react"
import ModalList from './ModalList'
import { useAppSelector } from "../../ducks";


export default function PureModal() {
    const activeModal = useAppSelector(state => state.ui.modal.activeModal)
    const ActiveModal = ModalList.find(m => m.name === activeModal )

    return(
        activeModal ? <ActiveModal/> : <div/>
    )
}
