import { ModeState, RawSpecParts } from ".";

export interface Process {
    is_visible: boolean;
    executable: string;
    is_system: string;
    display_name: string;
}

export interface LocalState extends ModeState {
    isLoading: boolean;
    currentProcesses: Process[];
    selectedProcesses?: string;
}

export const getSpec = (m: LocalState): string => {
    return m.selectedProcesses ? `local:${m.selectedProcesses}` : "local";
};

export const parseRaw = ({ data }: RawSpecParts): LocalState => ({
    ui_id: Math.random(),
    active: true,
    isLoading: false,
    currentProcesses: [],
    selectedProcesses: data,
});
