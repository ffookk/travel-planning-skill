function mobileDevice() {
  if (
    navigator.userAgentData &&
    typeof navigator.userAgentData.mobile === "boolean"
  ) {
    return navigator.userAgentData.mobile;
  }
  return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
}

function loadMap(frame, mobile) {
  const mobileSource = frame.dataset.mobileSrc || "";
  const target = mobile && mobileSource ? mobileSource : frame.dataset.src;
  if (target && (!frame.src || frame.src === "about:blank" || frame.src !== target)) {
    frame.src = target;
  }
}

function fallbackCopy(text) {
  const field = document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.appendChild(field);
  field.select();
  const copied = document.execCommand("copy");
  field.remove();
  return copied;
}

function fullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement;
}

function openActiveMap(map, mobile) {
  const frame = map.querySelector(".route-map-frame");
  if (!frame) return;
  const mobileSource = frame.dataset.mobileSrc || "";
  const fallback = mobile && mobileSource ? mobileSource : frame.dataset.src;
  const url = frame.src && frame.src !== "about:blank" ? frame.src : fallback;
  if (url) window.open(url, "_blank", "noopener,noreferrer");
}

export function enhancePage() {
  const cleanups = [];
  const mobile = mobileDevice();
  const mapFrames = Array.from(
    document.querySelectorAll(".route-map-frame[data-src]"),
  );
  let mapObserver = null;

  if ("IntersectionObserver" in window) {
    mapObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          loadMap(entry.target, mobile);
          mapObserver.unobserve(entry.target);
        });
      },
      { rootMargin: "500px 0px" },
    );
    mapFrames.forEach((frame) => mapObserver.observe(frame));
    cleanups.push(() => mapObserver.disconnect());
  } else if (mapFrames[0]) {
    loadMap(mapFrames[0], mobile);
  }

  const fullscreenButtons = Array.from(
    document.querySelectorAll(".route-map-fullscreen"),
  );
  const syncFullscreenButtons = () => {
    fullscreenButtons.forEach((button) => {
      const active = fullscreenElement() === button.closest(".route-map");
      button.textContent = active ? "退出全屏" : "全屏查看";
      button.setAttribute("aria-pressed", String(active));
    });
  };
  const onFullscreenChange = () => syncFullscreenButtons();
  document.addEventListener("fullscreenchange", onFullscreenChange);
  document.addEventListener("webkitfullscreenchange", onFullscreenChange);
  cleanups.push(() => {
    document.removeEventListener("fullscreenchange", onFullscreenChange);
    document.removeEventListener("webkitfullscreenchange", onFullscreenChange);
  });

  fullscreenButtons.forEach((button) => {
    const onClick = () => {
      const map = button.closest(".route-map");
      if (!map) return;
      if (fullscreenElement() === map) {
        const exit = document.exitFullscreen || document.webkitExitFullscreen;
        if (exit) exit.call(document);
        return;
      }
      const enter = map.requestFullscreen || map.webkitRequestFullscreen;
      if (!enter) {
        openActiveMap(map, mobile);
        return;
      }
      try {
        const pending = enter.call(map);
        if (pending && pending.catch) {
          pending.catch(() => openActiveMap(map, mobile));
        }
      } catch (_error) {
        openActiveMap(map, mobile);
      }
    };
    button.addEventListener("click", onClick);
    cleanups.push(() => button.removeEventListener("click", onClick));
  });

  document.querySelectorAll("[data-wechat-account]").forEach((button) => {
    const onClick = async () => {
      const account = button.dataset.wechatAccount || "";
      const menu = button.dataset.wechatMenu || "";
      const actions = button.closest(".actions");
      const status = actions
        ? actions.querySelector(".wechat-account-status")
        : null;
      let copied = false;
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(account);
          copied = true;
        } else {
          copied = fallbackCopy(account);
        }
      } catch (_error) {
        copied = fallbackCopy(account);
      }
      if (status) {
        status.textContent = copied
          ? `已复制“${account}”，请打开微信搜索${menu ? `，再进入“${menu}”` : ""}。`
          : `请打开微信搜索“${account}”${menu ? `，再进入“${menu}”` : ""}。`;
      }
      if (copied) {
        const original = button.textContent;
        button.textContent = "已复制，打开微信搜索";
        window.setTimeout(() => {
          button.textContent = original;
        }, 2400);
      }
    };
    button.addEventListener("click", onClick);
    cleanups.push(() => button.removeEventListener("click", onClick));
  });

  return {
    viewChanged(view) {
      if (view !== "routes") return;
      window.requestAnimationFrame(() => {
        mapFrames.forEach((frame) => {
          const box = frame.getBoundingClientRect();
          if (box.top < window.innerHeight + 500 && box.bottom > -500) {
            loadMap(frame, mobile);
            if (mapObserver) mapObserver.unobserve(frame);
          }
        });
      });
    },
    destroy() {
      cleanups.reverse().forEach((cleanup) => cleanup());
    },
  };
}
