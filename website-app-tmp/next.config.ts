import { networkInterfaces } from "node:os";
import type { NextConfig } from "next";

function localIpv4DevOrigins() {
  const origins = new Set<string>();
  for (const addresses of Object.values(networkInterfaces())) {
    for (const address of addresses ?? []) {
      if (!address.internal && address.family === "IPv4") {
        origins.add(address.address);
      }
    }
  }
  return [...origins];
}

const nextConfig: NextConfig = {
  // Next dev blocks LAN hosts unless they are explicitly allowed.
  allowedDevOrigins: localIpv4DevOrigins(),
  typedRoutes: true,
};

export default nextConfig;
