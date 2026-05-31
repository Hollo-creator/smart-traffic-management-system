"use strict";

// ── Socket.IO connection ───────────────────────────────
const socket = io();
const DIRS   = ["north", "east", "south", "west"];

// ── Live chart (rolling 30-point window) ──────────────
const liveCtx  = document.getElementById("liveChart").getContext("2d");
const CHART_WINDOW = 30;
const liveData = {
  labels:   Array(CHART_WINDOW).fill(""),
  datasets: DIRS.map((d, i) => ({
    label: d.charAt(0).toUpperCase() + d.slice(1),
    data:  Array(CHART_WINDOW).fill(0),
    borderColor:     ["#3b82f6","#22c55e","#f59e0b","#a855f7"][i],
    backgroundColor: ["#3b82f620","#22c55e20","#f59e0b20","#a855f720"][i],
    tension: 0.35,
    fill: true,
    pointRadius: 0,
  })),
};
const liveChart = new Chart(liveCtx, {
  type: "line",
  data: liveData,
  options: {
    animation: false,
    scales: {
      x: { display: false },
      y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.06)" },
           ticks: { color: "#8b90a0" } },
    },
    plugins: { legend: { labels: { color: "#8b90a0", boxWidth: 12 } } },
  },
});

// ── Hourly chart ───────────────────────────────────────
const hourlyCtx = document.getElementById("hourlyChart").getContext("2d");
let hourlyChart = null;

function renderHourlyChart(summaryData) {
  const hours = [...new Set(summaryData.map(r => r.hour))].sort();
  const datasets = DIRS.map((d, i) => {
    const dKey = d.charAt(0).toUpperCase() + d.slice(1);
    return {
      label: dKey,
      data:  hours.map(h => {
        const row = summaryData.find(r => r.direction === dKey && r.hour === h);
        return row ? row.avg_count : 0;
      }),
      backgroundColor: ["#3b82f670","#22c55e70","#f59e0b70","#a855f770"][i],
      borderColor:     ["#3b82f6","#22c55e","#f59e0b","#a855f7"][i],
      borderWidth: 1,
    };
  });

  if (hourlyChart) hourlyChart.destroy();
  hourlyChart = new Chart(hourlyCtx, {
    type: "bar",
    data: { labels: hours.map(h => h + ":00"), datasets },
    options: {
      scales: {
        x: { ticks: { color: "#8b90a0" }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { color: "#8b90a0" },
             grid: { color: "rgba(255,255,255,0.06)" } },
      },
      plugins: { legend: { labels: { color: "#8b90a0", boxWidth: 12 } } },
    },
  });
}

// ── Counts per direction (latest) ─────────────────────
const latestCounts = { north: 0, east: 0, south: 0, west: 0 };

// ── Clock ──────────────────────────────────────────────
function updateClock() {
  document.getElementById("clock").textContent =
    new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ── Helpers ────────────────────────────────────────────
function updateStatsBar() {
  const total = Object.values(latestCounts).reduce((s, v) => s + v, 0);
  document.getElementById("total-vehicles").textContent = total;

  const busiest = Object.entries(latestCounts)
    .sort((a, b) => b[1] - a[1])[0];
  document.getElementById("busiest-dir").textContent =
    busiest[0].charAt(0).toUpperCase() + busiest[0].slice(1);
}

function pushLiveChart(dir, count) {
  const ds = liveData.datasets.find(d => d.label.toLowerCase() === dir);
  if (!ds) return;
  const now = new Date().toLocaleTimeString();
  liveData.labels.push(now);
  liveData.labels.shift();
  ds.data.push(count);
  ds.data.shift();
  liveChart.update("none");   // no animation for performance
}

function addLogRow(data, direction) {
  const tbody = document.getElementById("logBody");
  const tr    = document.createElement("tr");
  const ts    = new Date().toLocaleTimeString();
  tr.innerHTML = `
    <td>${ts}</td>
    <td>${direction}</td>
    <td>${data.count}</td>
    <td>${data.green_sec}</td>
    <td class="${data.emergency ? 'badge-emergency' : 'badge-normal'}">
      ${data.emergency ? "🚨 YES" : "—"}
    </td>`;
  tbody.prepend(tr);
  // Keep at most 50 rows
  while (tbody.rows.length > 50) tbody.deleteRow(-1);
}

// ── Per-direction frame handler ────────────────────────
DIRS.forEach(dir => {
  socket.on(`frame_${dir}`, data => {
    // Update camera feed
    document.getElementById(`frame-${dir}`).src =
      `data:image/jpeg;base64,${data.image}`;

    // Update overlay labels
    document.getElementById(`count-${dir}`).textContent =
      `Vehicles: ${data.count}`;
    document.getElementById(`timer-${dir}`).textContent =
      `Green: ${data.green_sec}s`;

    // Update signal pill
    const pill = document.getElementById(`pill-${dir}`);
    const card = document.getElementById(`card-${dir}`);
    if (data.signal.toUpperCase() === "GREEN") {
      pill.textContent = "GREEN";
      pill.classList.add("green");
      card.classList.add("active-green");
      card.classList.remove("active-red");
    } else {
      pill.textContent = "RED";
      pill.classList.remove("green");
      card.classList.remove("active-green");
      card.classList.add("active-red");
    }

    // Emergency banner
    if (data.emergency) {
      const banner = document.getElementById("emergency-banner");
      banner.style.display = "";
      document.getElementById("emergency-dir").textContent = dir.toUpperCase();
    }

    // Charts
    latestCounts[dir] = data.count;
    updateStatsBar();
    pushLiveChart(dir, data.count);

    // Stats bar — active green direction
    if (data.signal.toUpperCase() === "GREEN") {
      document.getElementById("active-green").textContent =
        dir.charAt(0).toUpperCase() + dir.slice(1);
    }

    // Log table (every ~10 events per direction)
    if (Math.random() < 0.1) addLogRow(data, dir);
  });
});

// ── Signal update (from signal_controller) ────────────
socket.on("signal_update", status => {
  const active = status.active_direction;
  DIRS.forEach(dir => {
    const pill = document.getElementById(`pill-${dir}`);
    const card = document.getElementById(`card-${dir}`);
    const info = status.directions?.[dir.charAt(0).toUpperCase() + dir.slice(1)];
    if (!info) return;

    if (info.signal.toUpperCase() === "GREEN") {
      pill.textContent = "GREEN"; pill.classList.add("green");
      card.classList.add("active-green"); card.classList.remove("active-red");
    } else {
      pill.textContent = "RED"; pill.classList.remove("green");
      card.classList.remove("active-green"); card.classList.add("active-red");
    }
  });
  if (active) {
    document.getElementById("active-green").textContent = active;
  }
});

// ── REST helpers ───────────────────────────────────────
async function startSystem() {

    console.log("START BUTTON CLICKED");

    document.getElementById(
        "btnStart"
    ).disabled = true;

    const response = await fetch("/api/start", {
        method: "POST"
    });

    const data = await response.json();

    console.log(data);
}

async function stopSystem() {

    const response = await fetch("/api/stop", {
        method: "POST"
    });

    const data = await response.json();

    console.log(data);

    // Reset all frames to placeholder
    ["north", "east", "south", "west"]
    .forEach(dir => {

        document.getElementById(
            `frame-${dir}`
        ).src =
            "/static/img/placeholder.svg";

        document.getElementById(
            `count-${dir}`
        ).innerText =
            "Vehicles: 0";

        document.getElementById(
            `timer-${dir}`
        ).innerText =
            "Green: 0s";

        const pill = document.getElementById(
            `pill-${dir}`
        );

        pill.innerText = "RED";

        pill.style.background = "#ef4444";
    });

    // Reset stats
    document.getElementById(
        "total-vehicles"
    ).innerText = "0";

    document.getElementById(
        "busiest-dir"
    ).innerText = "—";

    document.getElementById(
        "active-green"
    ).innerText = "—";

    // Enable start button again
    document.getElementById(
        "btnStart"
    ).disabled = false;
}


async function loadHourly() {
  const res  = await fetch("/api/summary");
  const data = await res.json();
  if (data.length) renderHourlyChart(data);
}

// ── Init ───────────────────────────────────────────────
loadHourly();
setInterval(loadHourly, 60_000);   // refresh hourly chart every minute
window.startSystem = startSystem;
window.stopSystem = stopSystem;