import * as React from "react";
import FlowRow from "../../../components/FlowTable/FlowRow";
import { fireEvent, render, screen } from "../../test-utils";
import { TStore } from "../../ducks/tutils";

test("FlowRow", async () => {
    const store = TStore();
    const tflow = store.getState().flows.list[3];
    const { asFragment } = render(
        <table>
            <tbody>
                <FlowRow flow={tflow} selected highlighted />
            </tbody>
        </table>,
        { store },
    );
    expect(asFragment()).toMatchSnapshot();

    expect(store.getState().flows.selected[0]).not.toBe(tflow.id);
    fireEvent.click(screen.getByText("QUERY"));
    expect(store.getState().flows.selected[0]).toBe(tflow.id);
});
