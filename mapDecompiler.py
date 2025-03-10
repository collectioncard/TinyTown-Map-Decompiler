import os
import json
from PIL import Image

# Adjustable variables
TILE_SIZE = 16
MAIN_IMAGE_SIZE = 320  # Must be a multiple of TILE_SIZE

def process_tilemap(tilemap_path):
    img = Image.open(tilemap_path).convert('RGBA')
    width, height = img.size

    if width % TILE_SIZE != 0 or height % TILE_SIZE != 0:
        raise ValueError(f"Tilemap dimensions must be multiples of {TILE_SIZE}.")

    cols = width // TILE_SIZE
    rows = height // TILE_SIZE
    total_tiles = cols * rows
    print(f"Processed {total_tiles} tiles from tilemap.")

    tiles = [img.crop((x, y, x + TILE_SIZE, y + TILE_SIZE)) for y in range(0, height, TILE_SIZE) for x in range(0, width, TILE_SIZE)]

    tile_hash = {tuple(tile.getdata()): tile_id for tile_id, tile in enumerate(tiles)}

    composite_list = []
    for base_id in range(3):
        base_tile = tiles[base_id]
        for overlay_id in range(3, len(tiles)):
            overlay_tile = tiles[overlay_id]
            composite = Image.new('RGBA', (TILE_SIZE, TILE_SIZE))
            composite.paste(base_tile, (0, 0))
            composite.paste(overlay_tile, (0, 0), overlay_tile)
            composite_list.append((tuple(composite.getdata()), overlay_id, base_id))

    return tiles, tile_hash, composite_list

def process_main_image(main_image_path, tiles, tile_hash, composite_list):
    img = Image.open(main_image_path).convert('RGBA')
    width, height = img.size

    if width != MAIN_IMAGE_SIZE or height != MAIN_IMAGE_SIZE:
        raise ValueError(f"Main image must be {MAIN_IMAGE_SIZE}x{MAIN_IMAGE_SIZE} pixels ({MAIN_IMAGE_SIZE // TILE_SIZE}x{MAIN_IMAGE_SIZE // TILE_SIZE} tiles).")

    main_tiles = [tuple(img.crop((x, y, x + TILE_SIZE, y + TILE_SIZE)).getdata()) for y in range(0, height, TILE_SIZE) for x in range(0, width, TILE_SIZE)]

    tile_grid = []
    original_grass_grid = []
    for i in range(MAIN_IMAGE_SIZE // TILE_SIZE):
        row = []
        original_grass_row = []
        for j in range(MAIN_IMAGE_SIZE // TILE_SIZE):
            current_tile = main_tiles[i * (MAIN_IMAGE_SIZE // TILE_SIZE) + j]
            tile_id = tile_hash.get(current_tile, -1)
            original_grass_id = -1
            if tile_id == -1:
                for composite, overlay_id, base_id in composite_list:
                    if composite == current_tile:
                        tile_id = overlay_id
                        original_grass_id = base_id
                        break
            row.append(tile_id)
            original_grass_row.append(original_grass_id)
        tile_grid.append(row)
        original_grass_grid.append(original_grass_row)

    return tile_grid, original_grass_grid

def save_tile_grid_as_json(tile_grid, original_grass_grid, json_output_path):
    grass_layer = []
    decor_layer = []

    for row, original_grass_row in zip(tile_grid, original_grass_grid):
        grass_row = []
        other_row = []
        for tile_id, original_grass_id in zip(row, original_grass_row):
            if tile_id in [0, 1, 2]:
                grass_row.append(tile_id)
                other_row.append(-1)
            else:
                grass_row.append(original_grass_id)
                other_row.append(tile_id)
        grass_layer.append(grass_row)
        decor_layer.append(other_row)

    output_data = {
        "grass_layer": grass_layer,
        "decor_layer": decor_layer
    }

    with open(json_output_path, 'w') as json_file:
        json.dump(output_data, json_file, indent=4)
    print(f"Tile grid saved to {json_output_path}.")

def recreate_image(grass_layer, decor_layer, tiles, output_image_path):
    img = Image.new('RGBA', (MAIN_IMAGE_SIZE, MAIN_IMAGE_SIZE))

    for i, (grass_row, decor_row) in enumerate(zip(grass_layer, decor_layer)):
        for j, (grass_id, decor_id) in enumerate(zip(grass_row, decor_row)):
            x, y = j * TILE_SIZE, i * TILE_SIZE
            if grass_id != -1:
                img.paste(tiles[grass_id], (x, y))
            if decor_id != -1:
                img.paste(tiles[decor_id], (x, y), tiles[decor_id])

    img.save(output_image_path)
    print(f"Recreated image saved to {output_image_path}")

def compare_images(image_path1, image_path2):
    img1 = Image.open(image_path1).convert('RGBA')
    img2 = Image.open(image_path2).convert('RGBA')

    if list(img1.getdata()) == list(img2.getdata()):
        print("The recreated image matches the original image.")
    else:
        print("The recreated image does not match the original image.")

# Usage
tilemap_path = 'tilemap.png'
input_folder = 'input_images'
output_folder = 'output_jsons'

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

tiles, tile_hash, composites = process_tilemap(tilemap_path)

for filename in os.listdir(input_folder):
    if filename.endswith('.png'):
        main_image_path = os.path.join(input_folder, filename)
        tile_grid, original_grass_grid = process_main_image(main_image_path, tiles, tile_hash, composites)
        json_output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}.json")
        save_tile_grid_as_json(tile_grid, original_grass_grid, json_output_path)

        # Recreate and compare the image
        with open(json_output_path, 'r') as json_file:
            data = json.load(json_file)
            grass_layer = data['grass_layer']
            decor_layer = data['decor_layer']

        recreated_image_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_recreated.png")
        recreate_image(grass_layer, decor_layer, tiles, recreated_image_path)
        compare_images(main_image_path, recreated_image_path)