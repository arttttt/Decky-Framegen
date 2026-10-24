import { definePlugin } from "@decky/api";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { DeveloperSection, LibrarySection, OptiScalerControls } from "./components";
import { useInstalledLibrary } from "./hooks/useInstalledLibrary";

function MainContent() {
  const { library, reload } = useInstalledLibrary();

  return (
    <>
      <OptiScalerControls library={library} />
      <LibrarySection onChanged={reload} />
      <DeveloperSection />
    </>
  );
}

export default definePlugin(() => ({
  name: "Decky Framegen",
  titleView: <div>Decky Framegen</div>,
  alwaysRender: true,
  content: <MainContent />,
  icon: <MdOutlineAutoAwesomeMotion />,
  onDismount() {
    console.log("Decky Framegen Plugin unmounted");
  },
}));
