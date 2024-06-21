import * as React from "react";
import ValidateEditor from "../../../components/editors/ValidateEditor";
import {
    fireEvent,
    render,
    screen,
    userEvent,
    waitFor,
} from "../../test-utils";

test("ValidateEditor", async () => {
    const onEditDone = jest.fn();
    const { asFragment } = render(
        <ValidateEditor
            content="ok"
            isValid={(x) => x.includes("ok")}
            onEditDone={onEditDone}
        />,
    );
    expect(asFragment()).toMatchSnapshot();

    userEvent.click(screen.getByText("ok"));

    screen.getByText("ok").innerHTML = "this is ok";

    fireEvent.blur(screen.getByText("this is ok"));

    await waitFor(() => expect(onEditDone).toBeCalledWith("this is ok"));
    onEditDone.mockClear();

    userEvent.click(screen.getByText("this is ok"));
    screen.getByText("this is ok").innerHTML = "wat";
    fireEvent.blur(screen.getByText("wat"));
    expect(screen.getByText("ok")).toBeDefined();
});
