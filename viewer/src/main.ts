import maplibregl from 'maplibre-gl';
import { Protocol } from 'pmtiles';
import baseStyle from './base-style.json' with { type: 'json' };

// Registers the pmtiles:// URL scheme so MapLibre can read tiles directly
// out of a single .pmtiles file via HTTP range requests, instead of needing
// a tile server.
const protocol = new Protocol();
maplibregl.addProtocol('pmtiles', protocol.tile);

const OVERLAY_SOURCE_ID = 'survey_extents';

// survey_extents.pmtiles sits next to this page (copied into viewer/public/
// by `just tiles`, then into docs/map/ by the Vite build) -- resolved via
// document.baseURI rather than a literal relative path so it still works
// once deployed under GitHub Pages' /metaken/map/ subpath (vite.config.ts
// base: './').
const pmtilesUrl = new URL('survey_extents.pmtiles', document.baseURI).href;

// Categorical colors (blue/aqua, slots 1-2) match the palette already used in
// docs/index.html's field-completeness charts.
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
      id: 'survey_extents_line',
      type: 'line',
      source: OVERLAY_SOURCE_ID,
      'source-layer': 'survey_extents',
      paint: {
        'line-color': ['match', ['get', 'surveyTypeCategory'], '地図メイン', '#1baf7a', '#2a78d6'],
        'line-width': ['interpolate', ['linear'], ['zoom'], 4, 0.4, 12, 1.2],
        'line-opacity': 0.8
      }
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
