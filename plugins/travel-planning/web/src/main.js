import { createApp } from "vue";

import App from "./App.vue";
import "./style.css";

const mountPoint = document.querySelector("main");
const controls = document.getElementById("itinerary-view-controls");

if (mountPoint && controls) {
  const panelIds = ["detail-view", "overview-view", "route-view"];
  const panels = Object.fromEntries(
    panelIds.map((id) => {
      const panel = document.getElementById(id);
      return [id, panel ? panel.innerHTML : ""];
    }),
  );
  const routePanel = document.getElementById("route-view");
  const trailing = [];
  let sibling = routePanel ? routePanel.nextElementSibling : null;
  while (sibling) {
    trailing.push(sibling.outerHTML);
    sibling = sibling.nextElementSibling;
  }
  createApp(App, { panels, tailHtml: trailing.join("") }).mount(mountPoint);
}
