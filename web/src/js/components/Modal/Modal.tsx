import * as React from "react";
import ModalList from "./ModalList";
import { useAppSelector } from "../../ducks";

export default function PureModal() {
    const activeModal = useAppSelector((state) => state.ui.modal.activeModal);
    const Modal = activeModal ? ModalList[activeModal] : undefined;
    if (Modal) {
        return <Modal />;
    } else {
        return <></>;
    }
}
