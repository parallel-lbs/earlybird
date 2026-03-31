const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://api.8pilot.io'
  : window.location.origin;
let mapData = null;
let map = null;

async function init() {
  try {
    const resp = await fetch(`${API_BASE}/map/geojson`);
    if (!resp.ok) throw new Error(`${resp.status}: ${resp.statusText}`);
    mapData = await resp.json();
  } catch (e) {
    document.getElementById('loader').innerHTML =
      `<div style="color:#e74c3c">Failed to load map data</div>
       <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-top:8px">
         Run POST /map/build first, then refresh.
       </div>`;
    return;
  }

  initMap();
  initLegend();
  initSearch(mapData);
  // Hide loader once map finishes initial render, or after timeout
  const loaderEl = document.getElementById('loader');
  const hideLoader = () => loaderEl.classList.add('done');
  map.once('idle', hideLoader);
  // Fallback timeout in case 'idle' never fires
  setTimeout(hideLoader, 20000);
}

function initMap() {
  map = new maplibregl.Map({
    container: 'map',
    preserveDrawingBuffer: true,
    style: {
      version: 8,
      sources: {},
      layers: [{
        id: 'background',
        type: 'background',
        paint: { 'background-color': '#0d1117' }
      }]
    },
    center: [0, 6],
    zoom: 1.8,
    minZoom: 0.5,
    maxZoom: 18,
    attributionControl: false
  });

  map.on('load', () => {
    // ── Split features by geometry type ──────────────
    const regionFeatures = (mapData.features || []).filter(
      f => f.properties.node_type === 'region'
    );
    const pointFeatures = (mapData.features || []).filter(
      f => f.properties.node_type !== 'region'
    );

    // ── Sources ─────────────────────────────────────
    map.addSource('regions', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: regionFeatures }
    });

    map.addSource('points', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: pointFeatures }
    });

    // ── Layers — Map of GitHub style (dots form territories) ──

    // 1. Region fills — very subtle source territory background
    map.addLayer({
      id: 'region-fills',
      type: 'fill',
      source: 'regions',
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': 0.02
      }
    });

    // 2. Item glow — only at higher zoom to avoid GPU overload
    map.addLayer({
      id: 'item-glow',
      type: 'circle',
      source: 'points',
      filter: ['==', ['get', 'node_type'], 'item'],
      minzoom: 4,
      paint: {
        'circle-radius': [
          'interpolate', ['linear'], ['zoom'],
          4, 8,
          6, 12,
          10, 18
        ],
        'circle-color': ['get', 'color'],
        'circle-opacity': [
          'interpolate', ['linear'], ['zoom'],
          4, 0.06,
          6, 0.1,
          10, 0.06
        ],
        'circle-blur': 1
      }
    });

    // 3. Item dots — the primary visual, like Map of GitHub
    map.addLayer({
      id: 'item-circles',
      type: 'circle',
      source: 'points',
      filter: ['==', ['get', 'node_type'], 'item'],
      paint: {
        'circle-radius': [
          'interpolate', ['linear'], ['zoom'],
          0, 3.5,
          1, 4,
          2, 5,
          4, 6.5,
          6, 8,
          10, 12
        ],
        'circle-color': ['get', 'color'],
        'circle-opacity': [
          'interpolate', ['linear'], ['zoom'],
          0, 0.85,
          2, 0.88,
          4, 0.9,
          8, 0.95
        ],
        'circle-stroke-width': 0
      }
    });

    // 4-6. Symbol layers — DEFERRED to prevent blocking circle rendering
    //       Font loading blocks the entire MapLibre pipeline, so we add
    //       symbol layers only after circles have finished their first render.
    const addSymbolLayers = () => {

    map.addLayer({
      id: 'category-labels',
      type: 'symbol',
      source: 'points',
      filter: ['==', ['get', 'node_type'], 'category'],
      layout: {
        'text-field': ['upcase', ['get', 'label']],
        'text-size': [
          'interpolate', ['linear'], ['zoom'],
          0, 14,
          2, 18,
          4, 22,
          6, 26
        ],
        'text-anchor': 'center',
        'text-allow-overlap': true,
        'text-font': ['Noto Sans Bold'],
        'text-letter-spacing': 0.12
      },
      paint: {
        'text-color': '#ffffff',
        'text-halo-color': 'rgba(13,17,23,0.85)',
        'text-halo-width': 2.5,
        'text-halo-blur': 1
      }
    });

    // 5. Subcategory labels — smaller, appear on zoom
    map.addLayer({
      id: 'subcategory-labels',
      type: 'symbol',
      source: 'points',
      filter: ['==', ['get', 'node_type'], 'subcategory'],
      minzoom: 3,
      layout: {
        'text-field': ['get', 'label'],
        'text-size': [
          'interpolate', ['linear'], ['zoom'],
          3, 10,
          5, 12,
          7, 14
        ],
        'text-anchor': 'center',
        'text-allow-overlap': false,
        'text-font': ['Noto Sans Regular'],
        'text-padding': 10
      },
      paint: {
        'text-color': 'rgba(200,220,240,0.6)',
        'text-opacity': [
          'interpolate', ['linear'], ['zoom'],
          2, 0,
          4, 0.7
        ],
        'text-halo-color': 'rgba(13,17,23,0.8)',
        'text-halo-width': 1.5
      }
    });

    // 6. Item labels — on deep zoom
    map.addLayer({
      id: 'item-labels',
      type: 'symbol',
      source: 'points',
      filter: ['==', ['get', 'node_type'], 'item'],
      minzoom: 7,
      layout: {
        'text-field': ['get', 'title'],
        'text-size': [
          'interpolate', ['linear'], ['zoom'],
          7, 9,
          10, 11,
          14, 13
        ],
        'text-anchor': 'top',
        'text-offset': [0, 0.8],
        'text-max-width': 14,
        'text-allow-overlap': false,
        'text-font': ['Noto Sans Regular']
      },
      paint: {
        'text-color': 'rgba(255,255,255,0.9)',
        'text-halo-color': 'rgba(13,17,23,0.9)',
        'text-halo-width': 1.5,
        'text-halo-blur': 0.5
      }
    });

    }; // end addSymbolLayers

    // Add symbol layers after a delay so circle rendering is not blocked by font loading.
    // Use setGlyphs() to avoid setStyle() which destroys rendering state.
    setTimeout(() => {
      map.setGlyphs('https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf');
      addSymbolLayers();
    }, 3000);

    // ── Interactions ─────────────────────────────────

    const tooltip = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: 'map-tooltip'
    });

    // Click on item dot: open detail panel
    map.on('click', 'item-circles', (e) => {
      e.originalEvent.stopPropagation();
      const props = e.features[0].properties;
      if (typeof props.authors === 'string') {
        try { props.authors = JSON.parse(props.authors); } catch { props.authors = []; }
      }
      openPanel(props);
    });

    // Hover cursors
    map.on('mouseenter', 'item-circles', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'item-circles', () => {
      map.getCanvas().style.cursor = '';
    });

    // Tooltip on item hover
    map.on('mousemove', 'item-circles', (e) => {
      const props = e.features[0].properties;
      const signals = [];
      if (props.upvotes) signals.push(`${props.upvotes}\u2191`);
      if (props.hn_points) signals.push(`${props.hn_points}pts`);
      if (props.github_stars) signals.push(`${props.github_stars}\u2605`);
      const sig = signals.length ? `<br><span class="tooltip-meta">${signals.join(' \u00b7 ')}</span>` : '';

      tooltip
        .setLngLat(e.lngLat)
        .setHTML(`<strong>${props.title}</strong>${sig}`)
        .addTo(map);
    });
    map.on('mouseleave', 'item-circles', () => tooltip.remove());

    // Update legend on zoom
    map.on('zoomend', updateLegendForZoom);

    // Auto-center: fit 90th-percentile bounds (trim outliers)
    const items = pointFeatures.filter(f => f.properties.node_type === 'item');
    if (items.length > 1) {
      const lngs = items.map(f => f.geometry.coordinates[0]).sort((a, b) => a - b);
      const lats = items.map(f => f.geometry.coordinates[1]).sort((a, b) => a - b);
      const lo = Math.floor(items.length * 0.02);
      const hi = Math.floor(items.length * 0.98);
      map.fitBounds([[lngs[lo], lats[lo]], [lngs[hi], lats[hi]]], {
        padding: 60, maxZoom: 3, animate: false
      });
    }
  });
}

// ── Legend ─────────────────────────────────────────────

// Source territory features (category nodes = data sources)
function getSourceFeatures() {
  return (mapData.features || []).filter(f => f.properties.node_type === 'category');
}

// Topic subcategory features within a source territory
function getTopicFeatures(sourceLabel) {
  return (mapData.features || []).filter(
    f => f.properties.node_type === 'subcategory' && f.properties.parent_category === sourceLabel
  );
}

// For backward compat with updateLegendForZoom
function getCategoryFeatures() {
  return getSourceFeatures();
}

function initLegend() {
  const sources = getSourceFeatures()
    .sort((a, b) => (b.properties.item_count || 0) - (a.properties.item_count || 0));

  renderLegend(sources);
}

function renderLegend(sources, expandedSource) {
  const container = document.getElementById('legend-items');
  const title = document.getElementById('legend-title');
  container.innerHTML = '';

  if (expandedSource) {
    title.textContent = expandedSource;

    const back = document.createElement('div');
    back.className = 'legend-back';
    back.innerHTML = '&larr; All sources';
    back.addEventListener('click', () => {
      renderLegend(getSourceFeatures().sort((a, b) =>
        (b.properties.item_count || 0) - (a.properties.item_count || 0)
      ));
    });
    container.appendChild(back);

    // Show topic categories within this source territory
    const topics = getTopicFeatures(expandedSource)
      .sort((a, b) => (b.properties.item_count || 0) - (a.properties.item_count || 0));

    topics.forEach(f => {
      const props = f.properties;
      const item = document.createElement('div');
      item.className = 'legend-item';
      item.innerHTML = `
        <span class="legend-dot" style="background:${props.color}"></span>
        <span class="legend-label">${props.label}</span>
        <span class="legend-count">${props.item_count || 0}</span>
      `;
      item.addEventListener('click', () => {
        map.flyTo({ center: f.geometry.coordinates, zoom: 6, duration: 1000 });
      });
      container.appendChild(item);
    });
  } else {
    title.textContent = 'Sources';

    sources.forEach(f => {
      const props = f.properties;
      const item = document.createElement('div');
      item.className = 'legend-item';
      item.innerHTML = `
        <span class="legend-dot" style="background:${props.source_color || props.color}"></span>
        <span class="legend-label" style="font-weight:600">${props.label}</span>
        <span class="legend-count">${props.item_count || 0}</span>
      `;
      item.addEventListener('click', () => {
        map.flyTo({ center: f.geometry.coordinates, zoom: 3.5, duration: 1000 });
        renderLegend(sources, props.label);
      });
      container.appendChild(item);
    });
  }
}

function updateLegendForZoom() {
  const zoom = map.getZoom();
  if (zoom < 3) {
    renderLegend(getSourceFeatures().sort((a, b) =>
      (b.properties.item_count || 0) - (a.properties.item_count || 0)
    ));
    return;
  }

  const center = map.getCenter();
  const sources = getSourceFeatures();
  let closest = null;
  let minDist = Infinity;

  sources.forEach(f => {
    const [lng, lat] = f.geometry.coordinates;
    const dist = Math.hypot(lng - center.lng, lat - center.lat);
    if (dist < minDist) {
      minDist = dist;
      closest = f;
    }
  });

  if (closest && zoom >= 3.5) {
    renderLegend(sources, closest.properties.label);
  }
}

function flyTo(coordinates) {
  map.flyTo({ center: coordinates, zoom: 7, duration: 800 });
}

init();
