import { createAction, createSlice, PayloadAction } from "@reduxjs/toolkit";

export const EVENTS_ADD = createAction<EventLogItem>("EVENTS_ADD");
export const EVENTS_RECEIVE = createAction<EventLogItem[]>("EVENTS_RECEIVE");

export enum LogLevel {
    debug = "debug",
    info = "info",
    web = "web",
    warn = "warn",
    error = "error",
}

export interface EventLogItem {
    id: string;
    message: string;
    level: LogLevel;
}

interface EventLogState {
    visible: boolean;
    filters: { [level in LogLevel]: boolean };
    list: EventLogItem[];
    view: EventLogItem[];
}

export const defaultState: EventLogState = {
    visible: false,
    filters: { debug: false, info: true, web: true, warn: true, error: true },
    list: [],
    view: [],
};

const eventLogSlice = createSlice({
    name: "eventLog",
    initialState: defaultState,
    reducers: {
        toggleVisibility: (state) => {
            state.visible = !state.visible;
        },
        toggleFilter: (state, action: PayloadAction<LogLevel>) => {
            state.filters[action.payload] = !state.filters[action.payload];
            state.view = state.list.filter((log) => state.filters[log.level]);
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(EVENTS_ADD, (state, { payload: logItem }) => {
                state.list.push(logItem);
                if (state.filters[logItem.level]) {
                    state.view.push(logItem);
                }
            })
            .addCase(EVENTS_RECEIVE, (state, action) => {
                state.list = action.payload;
                state.view = state.list.filter(
                    (log) => state.filters[log.level],
                );
            });
    },
});

export const { toggleVisibility, toggleFilter } = eventLogSlice.actions;
export default eventLogSlice.reducer;

export function add(message: string, level: LogLevel = LogLevel.web) {
    return EVENTS_ADD({
        id: Math.random().toString(),
        message,
        level,
    });
}
