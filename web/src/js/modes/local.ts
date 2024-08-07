import { ModeState } from ".";

export interface LocalState extends ModeState {
    applications?: string;
}

export const getSpec = (m: LocalState): string => {
    return m.applications ? `local:${m.applications}` : "local";
};
