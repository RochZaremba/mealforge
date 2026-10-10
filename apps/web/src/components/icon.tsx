export type IconName = "today" | "plan" | "recipes" | "kitchen" | "shopping" | "leaf" | "arrow" | "signal";
const paths: Record<IconName, React.ReactNode> = {
 today: <><path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17m10-10 1.4-1.4"/><circle cx="12" cy="12" r="4"/></>,
 plan: <><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18m-13 4h2m4 0h2"/></>,
 recipes: <><path d="M5 3h14v18H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm0 14h14M8 7h7m-7 4h5"/></>,
 kitchen: <><path d="M5 3v7m3-7v7m3-7v7M5 7h6m-3 3v11m10-18v18m0-18c-4 4-4 9 0 9"/></>,
 shopping: <><path d="m3 4 2 1 3 12h10l3-9H6m4 13h.01M18 21h.01"/></>,
 leaf: <><path d="M19 4C9 2 3 7 5 14c2 6 13 6 14-10Z"/><path d="m4 21 10-11m-4 4v-4m3 1h4"/></>,
 arrow: <path d="M5 12h14m-5-5 5 5-5 5"/>,
 signal: <><path d="M4 9a13 13 0 0 1 16 0M7 13a8 8 0 0 1 10 0m-7 4a3 3 0 0 1 4 0"/><circle cx="12" cy="21" r=".5"/></>,
};
export function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
 return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
