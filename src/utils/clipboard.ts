/** Copies text to the clipboard; whether it worked. Game mode's browser lacks a reliable
 *  navigator.clipboard, so a hidden input and execCommand go first. */
export const copyText = async (text: string): Promise<boolean> => {
  const input = document.createElement("input");
  input.value = text;
  input.style.position = "absolute";
  input.style.left = "-9999px";
  document.body.appendChild(input);
  input.focus();
  input.select();
  try {
    if (document.execCommand("copy")) return true;
  } catch {
    // falls through to navigator.clipboard
  } finally {
    document.body.removeChild(input);
  }
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error("copyText", err);
    return false;
  }
};
