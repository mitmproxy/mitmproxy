import * as React from "react";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import FlowRow from "../../../components/FlowTable/FlowRow";
import { fireEvent, render, screen } from "../../test-utils";
import { TStore } from "../../ducks/tutils";

enableFetchMocks();

test("FlowRow", async () => {
    const store = TStore();
    const displayColumnNames = store.getState().options.web_columns;
    const tflow0 = store.getState().flows.list[0];
    const tflow3 = store.getState().flows.list[3];
    const { asFragment } = render(
        <table>
            <tbody>
                <FlowRow
                    flow={tflow0}
                    selected={false}
                    highlighted={false}
                    displayColumnNames={displayColumnNames}
                    rowNumber={0}
                    height={32}
                />
                <FlowRow
                    flow={tflow3}
                    selected={false}
                    highlighted={false}
                    displayColumnNames={displayColumnNames}
                    rowNumber={3}
                    height={32}
                />
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

test("the quickactions column selects the row except on a button", async () => {
    fetchMock.mockResponse("");
    const store = TStore();
    const displayColumnNames = store.getState().options.web_columns;
    const tflow0 = store.getState().flows.list[0];
    const tflow3 = store.getState().flows.list[3];
    const { container } = render(
        <table>
            <tbody>
                <FlowRow
                    flow={tflow0}
                    selected={false}
                    highlighted={false}
                    displayColumnNames={displayColumnNames}
                    rowNumber={0}
                    height={32}
                />
                <FlowRow
                    flow={tflow3}
                    selected={false}
                    highlighted={false}
                    displayColumnNames={displayColumnNames}
                    rowNumber={3}
                    height={32}
                />
            </tbody>
        </table>,
        { store },
    );

    const [actions0, actions3] = container.querySelectorAll(
        "td.col-quickactions",
    ) as NodeListOf<HTMLElement>;

    // The empty space a wide column leaves next to the buttons.
    fireEvent.click(actions0);
    expect(store.getState().flows.selected).toEqual([tflow0]);

    // A column without any buttons at all.
    fireEvent.click(actions3);
    expect(store.getState().flows.selected).toEqual([tflow3]);

    fireEvent.click(actions0.querySelector(".quickaction")!);
    expect(store.getState().flows.selected).toEqual([tflow3]);
    expect(fetchMock).toHaveBeenCalledWith(
        `./flows/${tflow0.id}/resume`,
        expect.objectContaining({ method: "POST" }),
    );
});
