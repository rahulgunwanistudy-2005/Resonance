import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@fontsource/overpass/400.css";
import "@fontsource/overpass/500.css";
import "@fontsource/overpass/600.css";
import "@fontsource/overpass/700.css";
import "uplot/dist/uPlot.min.css";
import "./styles/console.css";
import App from "./App";
const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 3000 } },
});
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
