/**
 * TypeScript declaration file for filt.js
 * This file provides type definitions for the filter expression parser
 * Generated from PEG.js grammar for mitmproxy filter expressions
 */

export interface ParseOptions {
    startRule?: string;
}

export interface Location {
    line: number;
    column: number;
    seenCR: boolean;
}

export interface LocationRange {
    start: Location;
    end: Location;
}

export interface SyntaxError extends Error {
    message: string;
    expected: any[];
    found: string | null;
    location: LocationRange;
    name: "SyntaxError";
}

export interface SyntaxErrorConstructor {
    new (
        message: string,
        expected: any[],
        found: string | null,
        location: LocationRange,
    ): SyntaxError;
}

export interface FilterFunction {
    (flow: any): boolean;
    desc?: string;
}

export interface ParseResult extends FilterFunction {}

export interface Parser {
    SyntaxError: SyntaxErrorConstructor;
    parse(input: string, options?: ParseOptions): ParseResult;
}

declare const parser: Parser;
export default parser;
