import { useEffect } from "react";
import { useDispatch } from "react-redux";
import { onKeyDown, type OnKeyDownOptions } from "web/ducks/ui/keyboard";

export function useKeyboardNavigation({
  ref,
  ...options
}: {
  ref: React.RefObject<HTMLElement | null>;
} & OnKeyDownOptions) {
  const dispatch = useDispatch();

  useEffect(() => {
    const refElement = ref.current;
    if (!refElement) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      dispatch(onKeyDown(e, options));
    };

    refElement.addEventListener("keydown", handleKeyDown);

    return () => refElement.removeEventListener("keydown", handleKeyDown);
  }, [dispatch, options, ref]);
}
