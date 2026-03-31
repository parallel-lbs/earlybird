function openPanel(props) {
  const panel = document.getElementById('panel');
  const content = document.getElementById('panel-content');

  const signals = [];
  if (props.upvotes) signals.push({ label: `${props.upvotes} upvotes`, strong: props.upvotes > 20 });
  if (props.hn_points) signals.push({ label: `${props.hn_points} HN points`, strong: props.hn_points > 300 });
  if (props.github_stars) signals.push({ label: `${props.github_stars} GitHub \u2605`, strong: props.github_stars > 100 });
  if (props.citation_count) signals.push({ label: `${props.citation_count} citations`, strong: props.citation_count > 50 });
  if (props.downloads) signals.push({ label: `${Number(props.downloads).toLocaleString()} downloads`, strong: props.downloads > 10000 });
  if (props.likes) signals.push({ label: `${props.likes} likes`, strong: props.likes > 50 });

  const signalBadges = signals
    .map(s => `<span class="signal-badge ${s.strong ? 'strong' : ''}">${s.label}</span>`)
    .join('');

  const authors = Array.isArray(props.authors) && props.authors.length > 0
    ? `<div class="panel-authors">${props.authors.join(', ')}</div>`
    : '';

  const abstract = props.abstract
    ? `<div class="panel-abstract">${props.abstract}</div>`
    : '';

  const published = props.published
    ? `<div style="font-size:12px;color:rgba(255,255,255,0.35);margin-bottom:16px">Published: ${props.published}</div>`
    : '';

  // Taxonomy tags (category + subcategory)
  const catColor = props.color || '#4a90d9';
  let taxonomy = '';
  if (props.category || props.subcategory) {
    const parts = [];
    if (props.category) {
      parts.push(`<span class="panel-taxonomy-tag" style="background:${catColor}22;border:1px solid ${catColor}44;color:${catColor}">${props.category}</span>`);
    }
    if (props.subcategory) {
      parts.push(`<span class="panel-taxonomy-tag" style="background:${catColor}18;border:1px solid ${catColor}30;color:${catColor}cc">${props.subcategory}</span>`);
    }
    taxonomy = `<div class="panel-taxonomy">${parts.join('')}</div>`;
  } else if (props.cluster_label) {
    // Fallback for old data format
    taxonomy = `<div class="panel-cluster" style="background:${catColor}22;border:1px solid ${catColor}44;color:${catColor}">${props.cluster_label}</div>`;
  }

  const scoreDisplay = props.signal_score != null
    ? ` · Score: ${(props.signal_score * 100).toFixed(0)}%`
    : '';

  content.innerHTML = `
    <div class="panel-title">${props.title}</div>
    <div class="panel-source">${props.source || ''}${scoreDisplay}</div>
    ${taxonomy}
    ${abstract}
    ${signalBadges ? `<div class="panel-signals">${signalBadges}</div>` : ''}
    ${authors}
    ${published}
    ${props.url ? `<a href="${props.url}" target="_blank" rel="noopener" class="panel-link">Open &rarr;</a>` : ''}
  `;

  panel.classList.remove('hidden');
  panel.classList.add('open');
}

document.getElementById('panel-close').addEventListener('click', () => {
  const panel = document.getElementById('panel');
  panel.classList.remove('open');
  panel.classList.add('hidden');
});
