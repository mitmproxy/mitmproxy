import * as React from "react";
import FlowRow from "../../../components/FlowTable/FlowRow";
import { fireEvent, render, screen } from "../../test-utils";
import { TStore } from "../../ducks/tutils";

test("FlowRow", async () => {
    const store = TStore();
    const tflow0 = store.getState().flows.list[0];
    const tflow3 = store.getState().flows.list[3];
    const { asFragment } = render(
        <table>
            <tbody>
                <FlowRow flow={tflow0} selected={false} highlighted={false} />
                <FlowRow flow={tflow3} selected={false} highlighted={false} />
            </tbody>
        </table>,
        { store },
    );

    expect(asFragment()).toMatchSnapshot();
    expect(store.getState().flows.selected).not.toContain(tflow3);

    // Click once to select `tflow3`
    fireEvent.click(screen.getByText("QUERY"));
    expect(store.getState().flows.selected).toEqual([tflow3]);

    // Ctrl+Click to select `tflow0` as well
    fireEvent.click(screen.getByText("http://address:22/path"), {
        ctrlKey: true,
    });
    expect(store.getState().flows.selected).toEqual(
        expect.arrayContaining([tflow0, tflow3]),
    );

    // Ctrl+Click to select `tflow0` again --> deselect `tflow0`
    fireEvent.click(screen.getByText("http://address:22/path"), {
        ctrlKey: true,
    });
    expect(store.getState().flows.selected).toEqual(
        expect.arrayContaining([tflow3]),
    );
});
