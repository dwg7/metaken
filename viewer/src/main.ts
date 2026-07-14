import maplibregl from 'maplibre-gl';
import type { MapGeoJSONFeature } from 'maplibre-gl';
import { Protocol } from 'pmtiles';
import baseStyle from './base-style.json' with { type: 'json' };

// Registers the pmtiles:// URL scheme so MapLibre can read tiles directly
// out of a single .pmtiles file via HTTP range requests, instead of needing
// a tile server.
const protocol = new Protocol();
maplibregl.addProtocol('pmtiles', protocol.tile);

const OVERLAY_SOURCE_ID = 'survey_extents';
const OVERLAY_SOURCE_LAYER = 'survey_extents';
const LINE_LAYER_ID = 'survey_extents_line';
// Invisible fill layer, purely a hover/hit target: the visible style is
// outline-only (no fill), but hit-testing only the 1px line would make
// hovering the polygon interior do nothing.
const HIT_LAYER_ID = 'survey_extents_hit';

// survey_extents.pmtiles sits next to this page (copied into viewer/public/
// by `just tiles`, then into docs/map/ by the Vite build) -- resolved via
// document.baseURI rather than a literal relative path so it still works
// once deployed under GitHub Pages' /metaken/map/ subpath (vite.config.ts
// base: './').
const pmtilesUrl = new URL('survey_extents.pmtiles', document.baseURI).href;

// Categorical colors (blue/aqua, slots 1-2) match the palette already used in
// docs/index.html's field-completeness charts.
function colorForCategory(category: string): string {
  return category === '地図メイン' ? '#1baf7a' : '#2a78d6';
}

const style: maplibregl.StyleSpecification = {
  version: 8,
  name: 'metaken survey extents',
  sources: {
    ...(baseStyle.sources as maplibregl.StyleSpecification['sources']),
    [OVERLAY_SOURCE_ID]: {
      type: 'vector',
      url: `pmtiles://${pmtilesUrl}`,
      attribution: '国土地理院 公共測量成果等メタデータ (metaken)'
    }
  },
  glyphs: baseStyle.glyphs,
  sprite: baseStyle.sprite,
  terrain: baseStyle.terrain as maplibregl.StyleSpecification['terrain'],
  layers: [
    ...(baseStyle.before as maplibregl.LayerSpecification[]),
    {
      id: LINE_LAYER_ID,
      type: 'line',
      source: OVERLAY_SOURCE_ID,
      'source-layer': OVERLAY_SOURCE_LAYER,
      paint: {
        'line-color': ['match', ['get', 'surveyTypeCategory'], '地図メイン', '#1baf7a', '#2a78d6'],
        'line-width': ['interpolate', ['linear'], ['zoom'], 4, 0.4, 12, 1.2],
        'line-opacity': 0.8
      }
    },
    {
      id: HIT_LAYER_ID,
      type: 'fill',
      source: OVERLAY_SOURCE_ID,
      'source-layer': OVERLAY_SOURCE_LAYER,
      paint: { 'fill-color': '#000000', 'fill-opacity': 0 }
    },
    ...((baseStyle as Record<string, unknown>).contours as maplibregl.LayerSpecification[]),
    ...(baseStyle.after as maplibregl.LayerSpecification[])
  ]
};

const map = new maplibregl.Map({
  container: 'map',
  style,
  center: [138.0, 38.0],
  zoom: 5,
  attributionControl: false,
  localIdeographFontFamily: 'sans-serif'
});

map.addControl(new maplibregl.NavigationControl());
map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
map.addControl(new maplibregl.TerrainControl({ source: 'mapterhorn', exaggeration: 1 }), 'top-right');

// --- Hover panel: metadata for the polygon(s) under the cursor -----------

const FIELD_LABELS: Record<string, string> = {
  fiscal_year: '年度',
  region_code: '地域',
  surveyTypeCategory: '種別',
  has_dataQualityInfo: '品質情報',
  coordinateReferenceSystem: 'CRS',
  source_file: 'ファイル'
};
const MAX_FEATURES_SHOWN = 30;

const introEl = document.getElementById('intro') as HTMLElement;
const infoEl = document.getElementById('feature-info') as HTMLElement;

function clearChildren(el: HTMLElement): void {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function showIntro(): void {
  infoEl.style.display = 'none';
  introEl.style.display = 'block';
  clearChildren(infoEl);
}

// Built via DOM APIs (textContent), not innerHTML, so title/abstract text
// from GSI's XML can never be interpreted as markup.
function renderFeatureInfo(features: MapGeoJSONFeature[]): void {
  clearChildren(infoEl);

  const count = document.createElement('p');
  count.className = 'count';
  count.textContent = `${features.length} 件`;
  infoEl.appendChild(count);

  for (const feature of features.slice(0, MAX_FEATURES_SHOWN)) {
    const props = feature.properties ?? {};

    const details = document.createElement('details');
    const summary = document.createElement('summary');

    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.background = colorForCategory(String(props.surveyTypeCategory ?? ''));
    summary.appendChild(swatch);

    const titleEl = document.createElement('span');
    titleEl.className = 'title';
    titleEl.textContent = String(props.title || props.source_file || '(無題)');
    summary.appendChild(titleEl);

    details.appendChild(summary);

    const dl = document.createElement('dl');
    for (const [key, label] of Object.entries(FIELD_LABELS)) {
      const value = props[key];
      if (!value) continue;
      const dt = document.createElement('dt');
      dt.textContent = label;
      const dd = document.createElement('dd');
      dd.textContent = String(value);
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    details.appendChild(dl);

    infoEl.appendChild(details);
  }

  if (features.length > MAX_FEATURES_SHOWN) {
    const note = document.createElement('p');
    note.className = 'truncated';
    note.textContent = `ほか ${features.length - MAX_FEATURES_SHOWN} 件`;
    infoEl.appendChild(note);
  }

  introEl.style.display = 'none';
  infoEl.style.display = 'block';
}

// The panel floats on top of the map (it's a DOM sibling of #map, not a
// descendant), so once the pointer is over the panel itself, map mousemove
// handling must not keep running underneath -- otherwise hovering the panel
// to read a record flickers it back to the intro state. Freeze panel updates
// for as long as the pointer is over the panel; the last state just stays put.
//
// This can't be done with a mouseleave listener on map.getContainer(): per
// the DOM spec, mouseleave/mouseenter fire based on DOM ancestry, not screen
// geometry -- moving onto .panel (a sibling of #map, not a descendant) counts
// as "leaving" #map even though panel sits entirely inside #map's own
// on-screen rectangle, and that leave fires *before* panel's own mouseenter
// sets the guard flag. So map.getContainer()'s mouseleave ran showIntro()
// unconditionally on every transition onto the panel, before the guard had
// a chance to engage. Tracking hover state on the panel itself (rather than
// reacting to the map "losing" the pointer) sidesteps the ordering problem.
const panelEl = document.querySelector('.panel') as HTMLElement;
let pointerOverPanel = false;
panelEl.addEventListener('mouseenter', () => {
  pointerOverPanel = true;
});
panelEl.addEventListener('mouseleave', () => {
  pointerOverPanel = false;
});

map.on('mousemove', (e) => {
  if (pointerOverPanel) return;
  const features = map.queryRenderedFeatures(e.point, { layers: [HIT_LAYER_ID] });
  map.getCanvas().style.cursor = features.length > 0 ? 'pointer' : '';
  if (features.length > 0) {
    renderFeatureInfo(features);
  } else {
    showIntro();
  }
});

// mousemove alone won't fire once the cursor leaves the browser viewport
// entirely, so the panel would otherwise stay stuck showing the
// last-hovered feature. Listen on the document, not map.getContainer(): the
// document has no DOM siblings, so this only fires on a genuine viewport
// exit, not on every transition onto a sibling element like the panel.
document.documentElement.addEventListener('mouseleave', () => {
  map.getCanvas().style.cursor = '';
  showIntro();
});
