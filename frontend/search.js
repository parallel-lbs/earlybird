let fuse = null;

function initSearch(mapData) {
  const features = mapData.features || [];

  // Index all searchable features (skip regions since they are polygons without meaningful search coords)
  const items = features
    .filter(f => f.properties.node_type !== 'region')
    .map(f => ({
      title: f.properties.title || f.properties.label || '',
      source: f.properties.source || '',
      node_type: f.properties.node_type || 'item',
      id: f.properties.id,
      coordinates: f.geometry.coordinates,
      properties: f.properties,
    }));

  fuse = new Fuse(items, {
    keys: ['title'],
    threshold: 0.4,
    includeScore: true,
  });

  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results');

  input.addEventListener('input', () => {
    const q = input.value.trim();
    if (q.length < 2) {
      results.style.display = 'none';
      return;
    }

    const matches = fuse.search(q).slice(0, 10);
    if (matches.length === 0) {
      results.style.display = 'none';
      return;
    }

    results.innerHTML = matches.map(m => {
      const nodeType = m.item.node_type;
      const label = m.item.title;
      const sourceTag = m.item.source
        ? `<span class="source-tag">${m.item.source}</span>`
        : '';
      const typeTag = nodeType !== 'item'
        ? `<span class="node-type-tag">${nodeType}</span>`
        : '';

      return `
        <div class="search-item" data-lng="${m.item.coordinates[0]}" data-lat="${m.item.coordinates[1]}" data-id="${m.item.id || ''}" data-node-type="${nodeType}">
          ${label}
          ${sourceTag}${typeTag}
        </div>
      `;
    }).join('');

    results.style.display = 'block';

    results.querySelectorAll('.search-item').forEach(el => {
      el.addEventListener('click', () => {
        const lng = parseFloat(el.dataset.lng);
        const lat = parseFloat(el.dataset.lat);
        const nodeType = el.dataset.nodeType;

        // Zoom level depends on node type
        let zoom = 7;
        if (nodeType === 'category') zoom = 3.5;
        else if (nodeType === 'subcategory') zoom = 6;

        map.flyTo({ center: [lng, lat], zoom, duration: 800 });

        results.style.display = 'none';
        input.value = '';

        // Open panel only for items
        if (nodeType === 'item') {
          const id = el.dataset.id;
          const feature = mapData.features.find(f => f.properties.id === id);
          if (feature) {
            const props = { ...feature.properties };
            if (typeof props.authors === 'string') {
              try { props.authors = JSON.parse(props.authors); } catch { props.authors = []; }
            }
            openPanel(props);
          }
        }
      });
    });
  });

  // Close results on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#search-bar')) {
      results.style.display = 'none';
    }
  });

  // Keyboard shortcut: / to focus search
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
    }
    if (e.key === 'Escape') {
      input.blur();
      results.style.display = 'none';
      document.getElementById('panel').classList.remove('open');
      document.getElementById('panel').classList.add('hidden');
    }
  });
}
