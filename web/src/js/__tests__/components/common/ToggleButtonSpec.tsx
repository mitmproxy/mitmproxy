import * as React from "react";
import renderer from "react-test-renderer";
import ToggleButton from "../../../components/common/ToggleButton";

describe("ToggleButton Component", () => {
    const mockFunc = jest.fn();

    it("should render correctly", () => {
        const checkedButton = renderer.create(
            <ToggleButton checked={true} onToggle={mockFunc} text="foo" />,
        );
        const tree = checkedButton.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should handle click action", () => {
        const uncheckButton = renderer.create(
            <ToggleButton checked={false} onToggle={mockFunc} text="foo" />,
        );
        const tree = uncheckButton.toJSON();
        tree.props.onClick();
        expect(mockFunc).toBeCalled();
    });
});
