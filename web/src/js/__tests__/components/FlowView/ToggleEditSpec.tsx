import React from 'react'
import ToggleEdit from '../../../components/FlowView/ToggleEdit'
import {TFlow} from '../../ducks/tutils'
import {render} from "../../test-utils"
import {fireEvent, screen} from "@testing-library/react";

let tflow = TFlow();

test("ToggleEdit", async () => {
    const {asFragment, store} = render(
        <ToggleEdit/>,
    );

    fireEvent.click(screen.getByTitle("Edit Flow"));
    expect(asFragment()).toMatchSnapshot();
    expect(store.getState().ui.flow.modifiedFlow).toBeTruthy();

    fireEvent.click(screen.getByTitle("Finish Edit"));
    expect(asFragment()).toMatchSnapshot();
    expect(store.getState().ui.flow.modifiedFlow).toBeFalsy();
});
