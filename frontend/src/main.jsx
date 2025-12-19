// Application Entry Point
// Renders the root React App component into the HTML element with id="root".
// Loads global CSS styles.
// React.StrictMode helps detect potential problems during development.

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);