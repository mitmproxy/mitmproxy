import * as React from "react";
import ViewSelector from "../../../components/contentviews/ViewSelector";
import { act, fireEvent, render, screen } from "../../test-utils";

test("ViewSelector", async () => {
    const onChange = jest.fn();
    const { asFragment } = render(
        <ViewSelector value="auto" onChange={onChange} />,
    );
    expect(asFragment()).toMatchSnapshot();

    await act(() => fireEvent.click(screen.getByText("auto")));
    expect(asFragment()).toMatchSnapshot();

    await act(() => fireEvent.click(screen.getByText("raw")));
    expect(onChange).toBeCalledWith("Raw");
});
