import * as React from "react";
import FilterDocs from "../../../components/Header/FilterDocs";
import { enableFetchMocks } from "jest-fetch-mock";
import { render, screen, waitFor } from "../../test-utils";

enableFetchMocks();

test("FilterDocs Component", async () => {
    fetchMock.mockOnceIf(
        "./filter-help",
        JSON.stringify({
            commands: [
                ["cmd1", "foo"],
                ["cmd2", "bar"],
            ],
        }),
    );

    const { asFragment } = render(<FilterDocs selectHandler={() => 0} />);

    expect(asFragment()).toMatchSnapshot();
    await waitFor(() => screen.getByText("cmd1"));
    expect(asFragment()).toMatchSnapshot();
});
