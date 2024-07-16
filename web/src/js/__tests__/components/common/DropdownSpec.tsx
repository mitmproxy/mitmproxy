import * as React from "react";
import Dropdown, {
    Divider,
    MenuItem,
    SubMenu,
} from "../../../components/common/Dropdown";
import { fireEvent, render, screen, waitFor } from "../../test-utils";

test("Dropdown", async () => {
    const onOpen = jest.fn();
    const { asFragment } = render(
        <Dropdown text="open me" onOpen={onOpen}>
            <MenuItem onClick={() => 0}>click me</MenuItem>
            <Divider />
            <MenuItem onClick={() => 0}>click me</MenuItem>
        </Dropdown>,
    );
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("open me"));
    await waitFor(() => expect(onOpen).toBeCalledWith(true));
    expect(asFragment()).toMatchSnapshot();

    onOpen.mockClear();
    fireEvent.click(document.body);
    await waitFor(() => expect(onOpen).toBeCalledWith(false));
});

test("SubMenu", async () => {
    const { asFragment } = render(
        <SubMenu title="submenu">
            <MenuItem onClick={() => 0}>click me</MenuItem>
        </SubMenu>,
    );
    expect(asFragment()).toMatchSnapshot();

    fireEvent.mouseEnter(screen.getByText("submenu"));
    await waitFor(() => screen.getByText("click me"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.mouseLeave(screen.getByText("submenu"));
    expect(screen.queryByText("click me")).toBeNull();
    expect(asFragment()).toMatchSnapshot();
});

test("MenuItem", async () => {
    const click = jest.fn();
    const { asFragment } = render(<MenuItem onClick={click}>wtf</MenuItem>);
    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("wtf"));
    await waitFor(() => expect(click).toBeCalled());
});
