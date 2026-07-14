"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

/**
 * Keeps the embedded App in sync with Kylon. When the Kylon shell asks the App
 * to refresh, for example after an agent updates App data from the App's
 * thread, this invalidates client-side App data so the latest API responses
 * are fetched in place, without a full reload.
 *
 * Registers with the Kylon bridge (`window.KylonBridge.onRefresh`). The bridge
 * script loads after hydration, so this also re-registers on the
 * `kylon:bridge-ready` event to avoid a load-order race. Outside Kylon (the App
 * opened directly in a browser) the bridge is absent and this is a no-op.
 */
export function KylonAutoRefresh() {
  const queryClient = useQueryClient();

  useEffect(() => {
    let unsubscribe: (() => void) | undefined;

    function register() {
      if (unsubscribe) return;
      unsubscribe = window.KylonBridge?.onRefresh?.(() => {
        void queryClient.invalidateQueries();
      });
    }

    register();
    window.addEventListener("kylon:bridge-ready", register);
    return () => {
      window.removeEventListener("kylon:bridge-ready", register);
      unsubscribe?.();
    };
  }, [queryClient]);

  return null;
}
