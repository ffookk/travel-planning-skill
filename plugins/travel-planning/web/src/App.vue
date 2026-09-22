<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { enhancePage } from "./pageEnhancements.js";

defineProps({
  panels: {
    type: Object,
    required: true,
  },
  tailHtml: {
    type: String,
    default: "",
  },
});

const views = [
  { id: "detail", label: "详细行程", panel: "detail-view" },
  { id: "overview", label: "行程一览", panel: "overview-view" },
  { id: "routes", label: "路线图", panel: "route-view" },
];
const activeView = ref("detail");
const tabElements = ref([]);
let pageEnhancements = null;

function applyView() {
  document.documentElement.dataset.itineraryView = activeView.value;
  if (pageEnhancements) pageEnhancements.viewChanged(activeView.value);
}

function selectView(view, focus = false) {
  activeView.value = view.id;
  if (window.history && window.history.replaceState) {
    window.history.replaceState(null, "", `#${view.panel}`);
  }
  if (focus) {
    nextTick(() => {
      const index = views.findIndex((item) => item.id === view.id);
      const element = tabElements.value[index];
      if (element) element.focus();
    });
  }
}

function onKeydown(event, index) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  let next = index;
  if (event.key === "Home") next = 0;
  else if (event.key === "End") next = views.length - 1;
  else if (event.key === "ArrowRight") next = (index + 1) % views.length;
  else next = (index - 1 + views.length) % views.length;
  selectView(views[next], true);
}

onMounted(() => {
  const hashView = views.find((view) => `#${view.panel}` === window.location.hash);
  if (hashView) activeView.value = hashView.id;
  pageEnhancements = enhancePage();
  document.documentElement.dataset.itineraryEnhanced = "true";
  applyView();
});

watch(activeView, applyView, { flush: "post" });

onBeforeUnmount(() => {
  if (pageEnhancements) pageEnhancements.destroy();
  delete document.documentElement.dataset.itineraryEnhanced;
  delete document.documentElement.dataset.itineraryView;
});
</script>

<template>
  <Teleport to="#itinerary-view-controls">
    <nav class="view-switcher" role="tablist" aria-label="行程展示方式">
      <a
        v-for="(view, index) in views"
        :key="view.id"
        :ref="(element) => { if (element) tabElements[index] = element; }"
        :href="`#${view.panel}`"
        role="tab"
        :aria-selected="String(activeView === view.id)"
        :aria-controls="view.panel"
        :tabindex="activeView === view.id ? 0 : -1"
        @click.prevent="selectView(view)"
        @keydown="onKeydown($event, index)"
      >
        {{ view.label }}
      </a>
    </nav>
  </Teleport>
  <section
    v-show="activeView === 'detail'"
    :hidden="activeView !== 'detail'"
    id="detail-view"
    data-itinerary-view="detail"
    v-html="panels['detail-view']"
  />
  <section
    v-show="activeView === 'overview'"
    :hidden="activeView !== 'overview'"
    id="overview-view"
    class="itinerary-overview"
    data-itinerary-view="overview"
    aria-labelledby="overview-heading"
    v-html="panels['overview-view']"
  />
  <section
    v-show="activeView === 'routes'"
    :hidden="activeView !== 'routes'"
    id="route-view"
    class="itinerary-routes"
    data-itinerary-view="routes"
    aria-labelledby="route-heading"
    v-html="panels['route-view']"
  />
  <div v-show="activeView !== 'routes'" class="itinerary-tail" v-html="tailHtml" />
</template>
