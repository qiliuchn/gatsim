# Create simulation map

## Create tileset and tilemap
Use tiled mapeditor to create a tilemap and tileset (town.json and town.tsx)

## Convert tilemap to  embed tilesets
python embed_tilesets.py city.json city_embedded.json

## Test tilemap
run a local server
```
cd map
python -m http.server 8000
```
then open http://localhost:8000