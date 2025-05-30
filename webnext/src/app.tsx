import { useEffect } from "react";
import { Header } from "@/components/header";
import { SideMenu } from "./components/sidemenu";
import { ThemeToggle } from "./components/theme-toggle";
import { Footer } from "./components/footer";
import { useDispatch } from "react-redux";
import { onKeyDown } from "web/ducks/ui/keyboard";
import { MainView } from "./components/main-view";

export function App() {
  /*   const showEventLog = useSelector(
    (state: RootState) => state.eventLog.visible,
  );
  const showCommandBar = useSelector(
    (state: RootState) => state.commandBar.visible,
  ); */
  // console.log({ showEventLog, showCommandBar }); // TODO: implement these features
  const dispatch = useDispatch();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      dispatch(onKeyDown(e));
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [dispatch]);

  return (
    <div className="font-inter bg-background text-foreground dark: flex h-screen flex-col">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <div className="bg-muted/20 relative w-64 border-r">
          <div className="p-3">
            <SideMenu />
          </div>

          <div className="border-border bg-muted/20 absolute right-0 bottom-0 left-0 border-t p-3">
            <ThemeToggle />
          </div>
        </div>

        <MainView />
      </div>

      <Footer />
    </div>
  );
}
