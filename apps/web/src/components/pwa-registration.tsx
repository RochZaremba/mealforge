"use client";
import { useEffect, useSyncExternalStore } from "react";
function subscribe(callback: () => void) {
 window.addEventListener("online", callback);
 window.addEventListener("offline", callback);
 return () => { window.removeEventListener("online", callback); window.removeEventListener("offline", callback); };
}
export function PwaRegistration() {
 const offline = useSyncExternalStore(subscribe, () => !navigator.onLine, () => false);
 useEffect(() => {
   if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
     navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => { /* Installation is optional; all online features remain usable. */ });
   }
 }, []);
 return offline ? <p className="offline-notice" role="status">Brak połączenia. Podgląd zapisanych planów i synchronizacja nie są jeszcze dostępne.</p> : null;
}
