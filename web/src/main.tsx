import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./design-system/index.css";
import "./app-layout.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
