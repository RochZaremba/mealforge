import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
 return { name: "MealForge — wspólna kuchnia", short_name: "MealForge", description: "Jedna kuchnia, osobne cele.", start_url: "/", scope: "/", display: "standalone", background_color: "#f7f6f2", theme_color: "#315b46", lang: "pl", icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" }, { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" }] };
}
