import { logError } from "../api";

/**
 * Safe wrapper for async operations to handle errors consistently
 * @param operation Async operation to perform
 * @param errorContext Context string for error logging
 */
export const safeAsyncOperation = async <T,>(
  operation: () => Promise<T>, 
  errorContext: string
): Promise<T | undefined> => {
  try {
    return await operation();
  } catch (e) {
    logError(`${errorContext}: ${String(e)}`);
    console.error(e);
    return undefined;
  }
};
