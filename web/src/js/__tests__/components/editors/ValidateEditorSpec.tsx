import * as React from "react"
import ValidateEditor from '../../../components/editors/ValidateEditor'
import {fireEvent, render, screen, waitFor} from "../../test-utils";

test("ValidateEditor", async () => {
    const onEditDone = jest.fn();
    const {asFragment} = render(
        <ValidateEditor content="ok" isValid={x => x.includes("ok")} onEditDone={onEditDone}/>
    );
    expect(asFragment()).toMatchSnapshot();

    fireEvent.mouseDown(screen.getByText("ok"));
    fireEvent.mouseUp(screen.getByText("ok"));

    screen.getByText("ok").innerHTML = "this is ok";

    fireEvent.blur(screen.getByText("this is ok"));

    await waitFor(() => expect(onEditDone).toBeCalledWith("this is ok"));
    onEditDone.mockClear();

    fireEvent.mouseDown(screen.getByText("this is ok"));
    fireEvent.mouseUp(screen.getByText("this is ok"));
    screen.getByText("this is ok").innerHTML = "wat";
    fireEvent.blur(screen.getByText("wat"));
    expect(screen.getByText("ok")).toBeDefined();
});
