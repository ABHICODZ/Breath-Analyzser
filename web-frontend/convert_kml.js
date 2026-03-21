const fs = require('fs');
const { DOMParser } = require('@xmldom/xmldom');
const toGeoJSON = require('@tmcw/togeojson');

try {
    const kmlText = fs.readFileSync('../archive_extracted/delhi_wards.kml', 'utf8');
    const parser = new DOMParser();
    const kmlDom = parser.parseFromString(kmlText, 'text/xml');
    
    // Convert to GeoJSON mathematically
    const geojson = toGeoJSON.kml(kmlDom);
    
    // Calculate centroids so the backend can poll chemistry data!
    if (geojson.features) {
        geojson.features.forEach((f, idx) => {
            let pts = [];
            const coords = f.geometry.coordinates;
            if (f.geometry.type === 'Polygon') {
                pts = [].concat(...coords);
            } else if (f.geometry.type === 'MultiPolygon') {
                pts = [].concat(...[].concat(...coords));
            }
            if (pts.length > 0) {
                const lats = pts.map(p => p[1]).filter(l => !isNaN(l));
                const lons = pts.map(p => p[0]).filter(l => !isNaN(l));
                f.properties.lat = lats.reduce((a, b) => a + b, 0) / lats.length;
                f.properties.lon = lons.reduce((a, b) => a + b, 0) / lons.length;
            }
            f.properties.ward_no = f.properties.name || `W_${idx}`;
        });
    }

    fs.writeFileSync('public/kaggle_wards.geojson', JSON.stringify(geojson));
    console.log(`SUCCESS: KML converted to Web-Native GeoJSON with ${geojson.features.length} polygons.`);
} catch (e) {
    console.error("KML Conversion Failed:", e);
}
