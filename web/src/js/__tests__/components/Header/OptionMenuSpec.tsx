import * as React from "react";
import OptionMenu from "../../../components/Header/OptionMenu";
import { fireEvent, render, screen, waitFor } from "../../test-utils";
import { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

describe("OptionMenu Component", () => {
    it("should render correctly", () => {
        const { asFragment } = render(<OptionMenu />);
        expect(asFragment()).toMatchSnapshot();
    });

    it("should update the web_theme option from the theme selector", async () => {
        fetchMock.mockResponseOnce("");

        render(<OptionMenu />);
        fireEvent.change(screen.getByDisplayValue("system"), {
            target: { value: "dark" },
        });

        await waitFor(() =>
            expect(fetchMock).toHaveBeenCalledWith(
                "./options",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({ web_theme: "dark" }),
                }),
            ),
        );
    });
});
