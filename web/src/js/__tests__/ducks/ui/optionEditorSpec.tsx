import reduceOptionsEditor, * as optionsEditorActions from "../../../ducks/ui/optionsEditor";
import { HIDE_MODAL } from "../../../ducks/ui/modal";
import { defaultState } from "../../../ducks/ui/optionsEditor";

describe("optionsEditor reducer", () => {
    it("should return initial state", () => {
        expect(defaultState).toEqual({});
    });

    it("should handle option update start", () => {
        const state = reduceOptionsEditor(
            undefined,
            optionsEditorActions.startUpdate({ option: "foo", value: "bar" }),
        );
        expect(state).toEqual({
            foo: { error: false, isUpdating: true, value: "bar" },
        });
    });

    it("should handle option update success", () => {
        expect(
            reduceOptionsEditor(
                undefined,
                optionsEditorActions.updateSuccess({ option: "foo" }),
            ),
        ).toEqual({ foo: undefined });
    });

    it("should handle option update error", () => {
        let state = reduceOptionsEditor(
            undefined,
            optionsEditorActions.startUpdate({ option: "foo", value: "bar" }),
        );
        state = reduceOptionsEditor(
            state,
            optionsEditorActions.updateError({
                option: "foo",
                error: "errorMsg",
            }),
        );
        expect(state).toEqual({
            foo: { error: "errorMsg", isUpdating: false, value: "bar" },
        });
        // boolean type
        state = reduceOptionsEditor(
            undefined,
            optionsEditorActions.startUpdate({ option: "foo", value: true }),
        );
        state = reduceOptionsEditor(
            state,
            optionsEditorActions.updateError({
                option: "foo",
                error: "errorMsg",
            }),
        );
        expect(state).toEqual({
            foo: { error: "errorMsg", isUpdating: false, value: false },
        });
    });

    it("should handle hide modal", () => {
        expect(reduceOptionsEditor(undefined, { type: HIDE_MODAL })).toEqual(
            {},
        );
    });
});
