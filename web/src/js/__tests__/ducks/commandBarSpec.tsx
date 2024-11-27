import reduceCommandBar, * as commandBarActions from "../../ducks/commandBar";

test("CommandBar", async () => {
    expect(reduceCommandBar(undefined, { type: "other" })).toEqual({
        visible: false,
    });
    expect(
        reduceCommandBar(undefined, commandBarActions.toggleVisibility()),
    ).toEqual({
        visible: true,
    });
});
