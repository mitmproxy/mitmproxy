import type { IconType } from "react-icons/lib";

export type FilterType =
  | "all"
  | "asset"
  | "body"
  | "requestBody"
  | "responseBody"
  | "responseCode"
  | "comment"
  | "domain"
  | "dns"
  | "destination"
  | "error"
  | "header"
  | "requestHeader"
  | "responseHeader"
  | "http"
  | "marked"
  | "marker"
  | "method"
  | "noResponse"
  | "clientReplay"
  | "serverReplay"
  | "replay"
  | "source"
  | "response"
  | "tcp"
  | "udp"
  | "requestContentType"
  | "responseContentType"
  | "contentType"
  | "url"
  | "websocket"
  | "bareString";

export type LogicalOperator = "AND" | "OR";

export type FilterCondition = {
  id: string;
  type: FilterType;
  value?: string;
  negate?: boolean;
  nextOperator?: LogicalOperator;
};

export type FilterGroup = {
  id: string;
  conditions: FilterCondition[];
  negate?: boolean;
  nextOperator?: LogicalOperator;
};

export type FilterCategoriesRecord = Record<
  string,
  { icon: IconType; color: string; filters: string[] }
>;

export type FilterDefinitionsRecord = Record<
  FilterType,
  {
    label: string;
    hasValue: boolean;
    symbol: string;
    icon: IconType;
    description: string;
  }
>;
