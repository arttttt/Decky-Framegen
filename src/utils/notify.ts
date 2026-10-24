import { toaster } from "@decky/api";
import { PLUGIN_TITLE } from "../presentation/plugin";

/** A toast from the plugin. */
export const notify = (body: string): void => {
  toaster.toast({ title: PLUGIN_TITLE, body });
};
