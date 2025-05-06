import json
import os
import sys
import xml.etree.ElementTree as ET

def embed_tilesets(input_file, output_file):
    """
    Convert a Tiled map JSON file with external tilesets to one with embedded tilesets.
    
    Args:
        input_file: Path to the input JSON file (the original Tiled map)
        output_file: Path where the modified JSON file will be saved
    """
    print(f"Converting {input_file} to {output_file}")
    
    try:
        # Load the map JSON file
        with open(input_file, 'r') as f:
            map_data = json.load(f)
        
        # Identify external tilesets that need to be embedded
        for tileset in map_data.get('tilesets', []):
            if 'source' in tileset:
                # This is an external tileset - we need to load and embed it
                tileset_path = tileset['source']
                # Get the directory of the map file to resolve relative paths
                map_dir = os.path.dirname(os.path.abspath(input_file))
                # Build the full path to the tileset file
                full_tileset_path = os.path.join(map_dir, tileset_path)
                
                print(f"Embedding external tileset: {tileset_path}")
                
                # Load the external tileset file (TSX is XML, not JSON)
                try:
                    # Parse the TSX (XML) file
                    tree = ET.parse(full_tileset_path)
                    root = tree.getroot()
                    
                    # Remove the 'source' attribute
                    firstgid = tileset.pop('source', None)
                    
                    # Extract properties from the XML
                    tileset['name'] = root.get('name')
                    tileset['tilewidth'] = int(root.get('tilewidth'))
                    tileset['tileheight'] = int(root.get('tileheight'))
                    tileset['tilecount'] = int(root.get('tilecount', 0))
                    tileset['columns'] = int(root.get('columns', 0))
                    
                    # Get image information
                    image_elem = root.find('image')
                    if image_elem is not None:
                        # Get the image path from the TSX
                        image_path = image_elem.get('source')
                        
                        # Handle relative paths - make the image path relative to the map directory
                        tileset_dir = os.path.dirname(full_tileset_path)
                        abs_image_path = os.path.normpath(os.path.join(tileset_dir, image_path))
                        rel_image_path = os.path.relpath(abs_image_path, map_dir)
                        
                        tileset['image'] = rel_image_path
                        tileset['imagewidth'] = int(image_elem.get('width', 0))
                        tileset['imageheight'] = int(image_elem.get('height', 0))
                    
                    # Extract tile properties if any
                    tiles = []
                    for tile_elem in root.findall('tile'):
                        tile_data = {
                            'id': int(tile_elem.get('id'))
                        }
                        
                        # Extract properties
                        properties_elem = tile_elem.find('properties')
                        if properties_elem is not None:
                            props = []
                            for prop in properties_elem.findall('property'):
                                props.append({
                                    'name': prop.get('name'),
                                    'type': prop.get('type', 'string'),
                                    'value': prop.get('value')
                                })
                            if props:
                                tile_data['properties'] = props
                        
                        tiles.append(tile_data)
                    
                    if tiles:
                        tileset['tiles'] = tiles
                    
                except Exception as e:
                    print(f"ERROR: Could not parse tileset file: {full_tileset_path}")
                    print(f"Error details: {str(e)}")
                    return False
        
        # Save the modified map with embedded tilesets
        with open(output_file, 'w') as f:
            json.dump(map_data, f, indent=2)
        
        print(f"Successfully converted map! Saved to {output_file}")
        return True
        
    except FileNotFoundError:
        print(f"ERROR: Could not find map file: {input_file}")
        return False
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in map file: {input_file}")
        return False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embed_tilesets.py input_map.json [output_map.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    # If no output file specified, create one with "_embedded" suffix
    if len(sys.argv) < 3:
        base_name, ext = os.path.splitext(input_file)
        output_file = f"{base_name}_embedded{ext}"
    else:
        output_file = sys.argv[2]
    
    success = embed_tilesets(input_file, output_file)
    sys.exit(0 if success else 1)