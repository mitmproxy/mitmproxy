import * as React from "react";
import ContentRenderer from "../../../components/contentviews/ContentRenderer";
import { fireEvent, render, screen } from "../../test-utils";

test("ContentRenderer", async () => {
    const content = `foo: 42\nbar: 43\n`;

    const showMore = jest.fn();
    const { asFragment } = render(
        <ContentRenderer content={content} maxLines={1} showMore={showMore} />,
    );
    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("Show more"));
    expect(showMore).toBeCalled();
});

test("No content", async () => {
    const { asFragment } = render(
        <ContentRenderer content={""} maxLines={1} showMore={() => 0} />,
    );
    expect(asFragment()).toMatchSnapshot();
});
