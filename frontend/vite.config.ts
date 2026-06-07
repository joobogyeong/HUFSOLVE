import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget = env.VITE_DEV_API_PROXY_TARGET;
  const wakeProxyTarget = env.VITE_DEV_WAKE_PROXY_TARGET;

  return {
    plugins: [react()],
    server: {
      proxy: {
        ...(apiProxyTarget
          ? {
              "/api": {
                target: apiProxyTarget,
                changeOrigin: true,
                rewrite: (path: string) => path.replace(/^\/api/, ""),
              },
            }
          : {}),
        ...(wakeProxyTarget
          ? {
              "/wake": {
                target: wakeProxyTarget,
                changeOrigin: true,
              },
            }
          : {}),
      },
    },
  };
});
