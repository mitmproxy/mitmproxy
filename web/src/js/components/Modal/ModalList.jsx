import React from 'react'
import ModalLayout from './ModalLayout'
import OptionContent from './OptionModal'
import CopyContent from './CopyModal'

function OptionModal() {
    return (
        <ModalLayout>
            <OptionContent/>
        </ModalLayout>
    )
}

function CopyModal() {
    return (
        <ModalLayout>
            <CopyContent/>
        </ModalLayout>
    )
}

export default [ OptionModal, CopyModal]
