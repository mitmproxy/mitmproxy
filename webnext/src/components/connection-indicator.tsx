import { StatusIndicator } from "@/components/ui/status-indicator";
import { ConnectionState } from "web/ducks/connection";
import { useAppSelector } from "web/ducks/hooks";
import { assertNever } from "web/utils";

export function ConnectionIndicator() {
  const connState = useAppSelector((state) => state.connection.state);
  const message = useAppSelector((state) => state.connection.message);

  switch (connState) {
    case ConnectionState.INIT:
      return (
        <StatusIndicator variant="info">
          <span>connecting...</span>
        </StatusIndicator>
      );
    case ConnectionState.FETCHING:
      return (
        <StatusIndicator variant="info">
          <span>fetching data...</span>
        </StatusIndicator>
      );
    case ConnectionState.ESTABLISHED:
      return (
        <StatusIndicator variant="success">
          <span>connected</span>
        </StatusIndicator>
      );
    case ConnectionState.ERROR:
      return (
        <StatusIndicator variant="error">
          <span title={message}>connection lost</span>
        </StatusIndicator>
      );
    default:
      assertNever(connState);
  }
}
