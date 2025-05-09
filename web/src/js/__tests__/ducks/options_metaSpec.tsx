import reduceOptionsMeta, * as OptionsMetaActions from "../../ducks/options_meta";
import * as OptionsActions from "../../ducks/options";
import { OptionsStateWithMeta } from "../../ducks/options";

test("options_meta", async () => {
    expect(reduceOptionsMeta(undefined, { type: "other" })).toEqual(
        OptionsMetaActions.defaultState,
    );

    // @ts-expect-error mocked
    let opts: OptionsStateWithMeta = { id: { value: "foo" } };
    expect(
        reduceOptionsMeta(undefined, OptionsActions.OPTIONS_RECEIVE(opts)),
    ).toEqual({ id: { value: "foo" } });

    expect(
        reduceOptionsMeta(undefined, OptionsActions.OPTIONS_UPDATE(opts)),
    ).toEqual({ ...OptionsMetaActions.defaultState, id: { value: "foo" } });
});
