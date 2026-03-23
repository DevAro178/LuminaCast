import json
import difflib

def calculate_unique_images(json_filepath: str, threshold: float = 0.65):
    # Load your response JSON
    with open(json_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    scenes = data.get("scenes", [])
    if not scenes:
        print("No scenes found in the JSON.")
        return

    # This will act as our simulated image pool
    unique_prompts = []
    
    for i, scene in enumerate(scenes):
        # Depending on the endpoint, the key might be 'image_prompt' or 'image_tags'
        # or 'edited_tags'. We'll fall back gracefully.
        target_prompt = scene.get("edited_tags") or scene.get("image_tags") or scene.get("image_prompt", "")
        
        best_ratio = 0.0
        
        # Compare current prompt against all unique prompts we've generated so far
        for pool_prompt in unique_prompts:
            ratio = difflib.SequenceMatcher(None, target_prompt, pool_prompt).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                
        # If it doesn't match anything closely enough, we must generate a new image
        if best_ratio < threshold:
            unique_prompts.append(target_prompt)

    total_scenes = len(scenes)
    unique_images = len(unique_prompts)
    reused_images = total_scenes - unique_images
    savings_pct = (reused_images / total_scenes) * 100 if total_scenes > 0 else 0

    print("--- Image Generation Pool Simulation ---")
    print(f"Total Scenes:      {total_scenes}")
    print(f"Unique Generators: {unique_images}")
    print(f"Reused Extant:     {reused_images}")
    print(f"API Time Savings:  {savings_pct:.1f}%")

# Run the simulation
if __name__ == "__main__":
    calculate_unique_images("response.json")
