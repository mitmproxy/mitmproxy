import * as React from "react";
import ModalList from "./ModalList";
import { useAppSelector } from "../../ducks";

function isModalName(name: string): name is keyof typeof ModalList {
    return name in ModalList;
}

export default function PureModal() {
    const activeModal = useAppSelector((state) => state.ui.modal.activeModal);
    const Modal =
        activeModal && isModalName(activeModal)
            ? ModalList[activeModal]
            : undefined;
    if (Modal) {
        return <Modal />;
    } else {
        return <></>;
    }
}
