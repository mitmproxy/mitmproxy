import * as React from "react";
import Modal from "../../../components/Modal/Modal";
import { render, act } from "../../test-utils";
import { setActiveModal } from "../../../ducks/ui/modal";

test("Modal Component", async () => {
    const { asFragment, store } = render(<Modal />);
    expect(asFragment()).toMatchSnapshot();

    act(() => store.dispatch(setActiveModal("OptionModal")));
    expect(asFragment()).toMatchSnapshot();
});
