import * as React from "react";
import ViewSelector from "../../../components/contentviews/ViewSelector";
import { fireEvent, render, screen } from "../../test-utils";

test("ViewSelector", async () => {
    const onChange = jest.fn();
    const { asFragment } = render(
        <ViewSelector value="Auto" onChange={onChange} />,
    );
    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("auto"));
    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("raw"));
    expect(onChange).toBeCalledWith("Raw");
});
