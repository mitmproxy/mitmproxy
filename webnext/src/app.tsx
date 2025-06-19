import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { MainView } from "@/components/main-view";

export function App() {
  /*   const showEventLog = useSelector(
    (state: RootState) => state.eventLog.visible,
  );
  const showCommandBar = useSelector(
    (state: RootState) => state.commandBar.visible,
  ); */
  // console.log({ showEventLog, showCommandBar }); // TODO: implement these features

  return (
    <div className="font-inter bg-background text-foreground dark: flex h-screen flex-col">
      <Header />
      <MainView />
      <Footer />
    </div>
  );
}
