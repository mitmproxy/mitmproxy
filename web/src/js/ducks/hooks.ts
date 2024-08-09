import { TypedUseSelectorHook, useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "./store";
import { createAsyncThunk } from "@reduxjs/toolkit";

// Use throughout your app instead of plain `useDispatch` and `useSelector`
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

export type AppAsyncThunkConfig = {
    state: RootState;
    dispatch: AppDispatch;
};

export const createAppAsyncThunk =
    createAsyncThunk.withTypes<AppAsyncThunkConfig>();
