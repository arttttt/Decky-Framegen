import { definePlugin } from "@decky/api";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { DeveloperSection, LibrarySection, OptiScalerControls } from "./components";
import { useInstalledLibrary } from "./hooks/useInstalledLibrary";
import { showReloadedPlugin } from "./api/deckyPanel";

function MainContent() {
  const { library, reload } = useInstalledLibrary();

  return (
    <>
      <OptiScalerControls library={library} />
      <LibrarySection library={library} onChanged={reload} />
      <DeveloperSection />
    </>
  );
}

export default definePlugin(() => {
  // After a self-update the loader stores this new plugin once this factory returns; the open
  // panel then still holds the old one, so it is asked to show this one on the next tick.
  window.setTimeout(showReloadedPlugin, 0);
  return {
    name: "Decky Framegen",
    titleView: <div>Decky Framegen</div>,
    alwaysRender: true,
    content: <MainContent />,
    icon: <MdOutlineAutoAwesomeMotion />,
    onDismount() {
      console.log("Decky Framegen Plugin unmounted");
    },
  };
});
