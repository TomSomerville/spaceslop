// SpaceSlop relay HUD: Mars clock, next-launch countdown, section filter, relative times.
(function () {
  const $$ = (sel) => document.querySelectorAll(sel);
  const pad = (n) => String(n).padStart(2, "0");
  const setAll = (sel, text) => $$(sel).forEach((el) => { el.textContent = text; });

  // Mars Sol Date and Coordinated Mars Time (Allison & McEwen 2000, as used by NASA GISS Mars24).
  function marsClock(now) {
    const jdUT = now / 86400000 + 2440587.5;
    const jdTT = jdUT + (37 + 32.184) / 86400;
    const msd = (jdTT - 2405522.0028779) / 1.0274912517;
    const h = (((msd % 1) + 1) % 1) * 24;
    const hh = Math.floor(h), mm = Math.floor((h - hh) * 60), ss = Math.floor(((h - hh) * 60 - mm) * 60);
    return { msd, sol: Math.floor(msd), mtc: `${pad(hh)}:${pad(mm)}:${pad(ss)}` };
  }

  function countdown(iso) {
    let s = Math.floor((new Date(iso) - Date.now()) / 1000);
    const sign = s < 0 ? "+" : "−";
    s = Math.abs(s);
    const d = Math.floor(s / 86400); s %= 86400;
    const h = Math.floor(s / 3600); s %= 3600;
    const m = Math.floor(s / 60); s %= 60;
    return `T${sign}${d ? d + "d " : ""}${pad(h)}:${pad(m)}:${pad(s)}`;
  }

  function ago(date) {
    const h = Math.round((Date.now() - date) / 3600000);
    if (h < 1) return "just now";
    if (h < 48) return `${h}h ago`;
    return `${Math.round(h / 24)}d ago`;
  }

  // Next launch: first from our own /assets/launches.json (refreshed by every newsroom
  // run), then from Launch Library 2 directly. Each request gives up after 8 seconds.
  let launch = null;
  async function getJSON(url) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 8000);
    try {
      const r = await fetch(url, { signal: ctl.signal, cache: "no-cache" });
      if (!r.ok) throw new Error(r.status);
      return await r.json();
    } finally {
      clearTimeout(timer);
    }
  }
  const pickNext = (list) => (list || []).find((l) => l && l.net && new Date(l.net) > Date.now() - 3600000);
  async function loadLaunch() {
    try {
      const c = JSON.parse(sessionStorage.getItem("ss-next-launch") || "null");
      if (c && Date.now() - c.t < 900000 && new Date(c.v.net) > Date.now() - 3600000) return c.v;
    } catch (e) {}
    let next = null;
    try {
      const base = document.querySelector('link[rel="stylesheet"][href*="style.css"]').getAttribute("href").split("/assets/")[0];
      next = pickNext((await getJSON(base + "/assets/launches.json")).upcoming);
    } catch (e) {}
    if (!next) {
      try { next = pickNext((await getJSON("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=5&mode=list")).results); } catch (e) {}
    }
    if (!next) return null;
    const v = { name: next.name, net: next.net };
    try { sessionStorage.setItem("ss-next-launch", JSON.stringify({ t: Date.now(), v })); } catch (e) {}
    return v;
  }
  loadLaunch().then((l) => {
    launch = l;
    if (!l) {
      setAll("[data-launch-name-full]", "Launch feed offline");
      setAll("[data-launch-count]", "T−--:--:--");
      return;
    }
    setAll("[data-launch-name]", "· " + l.name);
    setAll("[data-launch-name-full]", l.name);
    setAll("[data-launch-net]", new Date(l.net).toISOString().slice(0, 16).replace("T", " ") + " UTC");
    tick();
  });

  function tick() {
    const now = Date.now();
    const m = marsClock(now);
    setAll("[data-msd]", m.msd.toFixed(3));
    setAll("[data-mtc]", m.mtc);
    setAll("[data-sol]", m.sol.toLocaleString("en-US"));
    setAll("[data-utc]", new Date(now).toISOString().slice(11, 19));
    if (launch) setAll("[data-launch-count]", countdown(launch.net));
  }
  tick();
  setInterval(tick, 1000);

  $$("time[data-ago]").forEach((t) => { t.textContent = ago(new Date(t.getAttribute("datetime"))); });

  // Section filter on the home page (uses the URL hash, so links like /#launch work).
  const items = $$("[data-cat]");
  const empty = document.querySelector(".empty");
  const tabs = $$(".tab[data-filter]");
  const isHome = items.length > 0;
  function applyFilter() {
    const f = (location.hash || "#all").slice(1) || "all";
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.filter === f));
    if (!isHome) return;
    let shown = 0;
    items.forEach((el) => {
      const ok = f === "all" || el.dataset.cat === f;
      el.hidden = !ok;
      if (ok) shown++;
    });
    if (empty) empty.hidden = shown > 0;
  }
  if (isHome) {
    tabs.forEach((t) => t.addEventListener("click", (e) => {
      e.preventDefault();
      const f = t.dataset.filter;
      history.replaceState(null, "", f === "all" ? location.pathname : "#" + f);
      applyFilter();
    }));
    window.addEventListener("hashchange", applyFilter);
  }
  applyFilter();
})();
