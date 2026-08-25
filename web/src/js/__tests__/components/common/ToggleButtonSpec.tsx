import * as React from "react";
import ToggleButton from "../../../components/common/ToggleButton";
import { fireEvent, render, screen } from "../../test-utils";

describe("ToggleButton Component", () => {
    const mockFunc = jest.fn();

    it("should render correctly", () => {
        const { asFragment } = render(
            <ToggleButton checked={true} onToggle={mockFunc} text="foo" />,
        );
        expect(asFragment()).toMatchSnapshot();
        fireEvent.click(screen.getByText("foo"));
        expect(mockFunc).toBeCalled();
    });
});
