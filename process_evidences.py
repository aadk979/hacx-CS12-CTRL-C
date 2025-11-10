"""
Process evidence images using Google Gemini API for object detection.

This script processes all images associated with tags and generates:
- Object detections for each image
- A consolidated summary of the scene for each tag
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Error: google-genai package not installed.")
    print("   Install it with: pip install google-genai")
    sys.exit(1)

import config
from src.core.tag_manager import TagManager
from src.models.tag import Tag


class EvidenceProcessor:
    """Processes evidence images using Gemini API for object detection."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the evidence processor.
        
        Args:
            api_key: Google Gemini API key. If None, will try to get from environment.
        """
        try:
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                # Try to get from environment variable
                import os
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("API key not provided and GOOGLE_API_KEY not set")
                self.client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"❌ Error initializing Gemini client: {e}")
            print("   Make sure you have a valid Google API key.")
            sys.exit(1)
        
        self.tag_manager = TagManager()
        self.detections_dir = Path("data/evidence_detections")
        self.detections_dir.mkdir(parents=True, exist_ok=True)
        self.post_process_dir = Path("data/post_process")
        self.post_process_dir.mkdir(parents=True, exist_ok=True)
    
    def detect_objects_in_image(self, image_path: Path) -> Dict:
        """Detect objects in a single image using Gemini API.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing detections and metadata
        """
        try:
            # Open and validate image
            image = Image.open(image_path)
            width, height = image.size
            
            prompt = (
                "Detect all of the prominent items in the image. "
                "Return a JSON array of objects, each with 'label' (item name) and "
                "'box_2d' ([ymin, xmin, ymax, xmax] normalized to 0-1000). "
                "Only include clearly visible, prominent objects."
            )
            
            config_obj = types.GenerateContentConfig(
                response_mime_type="application/json"
            )
            
            print(f"  🔍 Processing: {image_path.name}...")
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image, prompt],
                config=config_obj
            )
            
            # Extract JSON text from response
            # Response structure: response.candidates[0].content.parts[0].text
            if not response.candidates or len(response.candidates) == 0:
                raise ValueError("No candidates in response")
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise ValueError("No content parts in response")
            
            text_part = candidate.content.parts[0].text
            if not text_part:
                raise ValueError("No text in response")
            
            # Parse response JSON
            bounding_boxes = json.loads(text_part)
            
            # Convert normalized coordinates to absolute pixel coordinates
            converted_bounding_boxes = []
            for detection in bounding_boxes:
                if "box_2d" in detection and len(detection["box_2d"]) == 4:
                    y1_norm, x1_norm, y2_norm, x2_norm = detection["box_2d"]
                    
                    abs_y1 = int(y1_norm / 1000 * height)
                    abs_x1 = int(x1_norm / 1000 * width)
                    abs_y2 = int(y2_norm / 1000 * height)
                    abs_x2 = int(x2_norm / 1000 * width)
                    
                    converted_detection = {
                        "label": detection.get("label", "unknown"),
                        "box_2d_absolute": [abs_x1, abs_y1, abs_x2, abs_y2],
                        "box_2d_normalized": detection["box_2d"],
                        "confidence": detection.get("confidence", 1.0)
                    }
                    converted_bounding_boxes.append(converted_detection)
            
            result = {
                "image_path": str(image_path),
                "image_size": {"width": width, "height": height},
                "detections": converted_bounding_boxes,
                "detection_count": len(converted_bounding_boxes)
            }
            
            print(f"  ✅ Found {len(converted_bounding_boxes)} objects")
            return result
            
        except Exception as e:
            print(f"  ❌ Error processing {image_path.name}: {e}")
            return {
                "image_path": str(image_path),
                "error": str(e),
                "detections": [],
                "detection_count": 0
            }
    
    def _get_color_for_object(self, object_name: str) -> Tuple[int, int, int]:
        """Generate a consistent color for an object name.
        
        Args:
            object_name: Name of the detected object
            
        Returns:
            RGB tuple (r, g, b) with values 0-255
        """
        # Use hash to generate consistent color for same object name
        hash_obj = hashlib.md5(object_name.lower().encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Generate bright, distinct colors
        r = (hash_int & 0xFF0000) >> 16
        g = (hash_int & 0x00FF00) >> 8
        b = hash_int & 0x0000FF
        
        # Ensure minimum brightness for visibility
        r = max(r, 50)
        g = max(g, 50)
        b = max(b, 50)
        
        # Normalize to ensure good contrast
        max_val = max(r, g, b)
        if max_val < 128:
            scale = 255 / max_val
            r = min(int(r * scale), 255)
            g = min(int(g * scale), 255)
            b = min(int(b * scale), 255)
        
        return (r, g, b)
    
    def _draw_bounding_boxes(self, image_path: Path, detections: List[Dict]) -> Image.Image:
        """Draw colored bounding boxes on an image.
        
        Args:
            image_path: Path to the original image
            detections: List of detection dictionaries with bounding boxes
            
        Returns:
            PIL Image with bounding boxes drawn
        """
        # Open image
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fallback to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                font = ImageFont.load_default()
        
        # Draw each bounding box
        for detection in detections:
            label = detection.get("label", "unknown")
            box = detection.get("box_2d_absolute", [])
            
            if len(box) != 4:
                continue
            
            x1, y1, x2, y2 = box
            
            # Get color for this object
            color = self._get_color_for_object(label)
            
            # Draw rectangle (outline)
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            # Draw semi-transparent fill
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([x1, y1, x2, y2], fill=(*color, 30))
            image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(image)
            
            # Draw label background
            label_text = f"{label}"
            bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Label position (above the box, or inside if box is at top)
            label_y = max(y1 - text_height - 5, 5)
            label_x = x1
            
            # Draw label background
            draw.rectangle(
                [label_x - 2, label_y - 2, label_x + text_width + 2, label_y + text_height + 2],
                fill=(*color, 200)
            )
            
            # Draw label text
            draw.text((label_x, label_y), label_text, fill=(255, 255, 255), font=font)
        
        return image
    
    def save_annotated_image(self, tag_id: str, image_path: Path, detections: List[Dict]) -> Optional[Path]:
        """Save an annotated image with bounding boxes.
        
        Args:
            tag_id: ID of the tag
            image_path: Path to the original image
            detections: List of detection dictionaries
            
        Returns:
            Path to the saved annotated image, or None if error
        """
        try:
            # Create tag-specific directory
            tag_post_dir = self.post_process_dir / tag_id
            tag_post_dir.mkdir(parents=True, exist_ok=True)
            
            # Draw bounding boxes
            annotated_image = self._draw_bounding_boxes(image_path, detections)
            
            # Generate output filename
            image_name = image_path.stem
            image_ext = image_path.suffix
            output_path = tag_post_dir / f"{image_name}_annotated{image_ext}"
            
            # Save annotated image
            annotated_image.save(output_path, quality=95)
            
            return output_path
            
        except Exception as e:
            print(f"  ⚠️  Error creating annotated image: {e}")
            return None
    
    def process_tag_photos(self, tag: Tag) -> Dict:
        """Process all photos for a specific tag.
        
        Args:
            tag: The tag to process
            
        Returns:
            Dictionary containing all detections and summary
        """
        print(f"\n📋 Processing tag: {tag.title} (ID: {tag.id})")
        print(f"   Location: ({tag.coords[0]:.2f}, {tag.coords[1]:.2f}, {tag.coords[2]:.2f})")
        
        if not tag.photos:
            print("  ⚠️  No photos found for this tag")
            return {
                "tag_id": tag.id,
                "tag_title": tag.title,
                "tag_description": tag.description,
                "tag_coords": tag.coords,
                "photos_processed": 0,
                "total_detections": 0,
                "image_detections": [],
                "summary": "No photos available for processing.",
                "detected_objects": []
            }
        
        print(f"  📸 Found {len(tag.photos)} photo(s)")
        
        # Process each photo
        image_detections = []
        all_detected_objects = []
        
        for photo_path_str in tag.photos:
            photo_path = Path(photo_path_str)
            
            if not photo_path.exists():
                print(f"  ⚠️  Photo not found: {photo_path}")
                image_detections.append({
                    "image_path": str(photo_path),
                    "error": "File not found",
                    "detections": [],
                    "detection_count": 0
                })
                continue
            
            # Detect objects in image
            detection_result = self.detect_objects_in_image(photo_path)
            image_detections.append(detection_result)
            
            # Create annotated image with bounding boxes
            if "error" not in detection_result and detection_result.get("detections"):
                annotated_path = self.save_annotated_image(
                    tag.id,
                    photo_path,
                    detection_result.get("detections", [])
                )
                if annotated_path:
                    detection_result["annotated_image_path"] = str(annotated_path)
                    print(f"  🎨 Saved annotated image: {annotated_path.name}")
            
            # Collect all detected objects for summary
            for det in detection_result.get("detections", []):
                all_detected_objects.append(det.get("label", "unknown"))
        
        # Generate consolidated summary
        summary = self._generate_summary(tag, image_detections, all_detected_objects)
        
        result = {
            "tag_id": tag.id,
            "tag_title": tag.title,
            "tag_description": tag.description,
            "tag_coords": tag.coords,
            "photos_processed": len([d for d in image_detections if "error" not in d]),
            "total_detections": sum(d.get("detection_count", 0) for d in image_detections),
            "image_detections": image_detections,
            "summary": summary,
            "detected_objects": list(set(all_detected_objects))  # Unique objects
        }
        
        return result
    
    def _generate_summary(self, tag: Tag, image_detections: List[Dict], 
                         all_objects: List[str]) -> str:
        """Generate a consolidated summary of the scene for a tag.
        
        Args:
            tag: The tag being processed
            image_detections: List of detection results for each image
            all_objects: List of all detected object labels
            
        Returns:
            Summary text
        """
        if not image_detections:
            return "No images were processed."
        
        # Count object occurrences
        from collections import Counter
        object_counts = Counter(all_objects)
        
        # Build summary
        summary_parts = [
            f"Evidence Analysis for Tag: {tag.title}",
            f"Location: ({tag.coords[0]:.2f}, {tag.coords[1]:.2f}, {tag.coords[2]:.2f})",
            f"Description: {tag.description}",
            "",
            f"Images Processed: {len(image_detections)}",
            f"Total Objects Detected: {len(all_objects)}",
            f"Unique Object Types: {len(object_counts)}",
            "",
            "Detected Objects:"
        ]
        
        # List objects by frequency
        for obj, count in object_counts.most_common():
            summary_parts.append(f"  - {obj}: {count} occurrence(s)")
        
        summary_parts.append("")
        summary_parts.append("Per-Image Details:")
        
        for idx, img_det in enumerate(image_detections, 1):
            img_path = Path(img_det.get("image_path", "unknown"))
            summary_parts.append(f"  Image {idx}: {img_path.name}")
            
            if "error" in img_det:
                summary_parts.append(f"    Error: {img_det['error']}")
            else:
                det_count = img_det.get("detection_count", 0)
                summary_parts.append(f"    Objects detected: {det_count}")
                
                for det in img_det.get("detections", []):
                    label = det.get("label", "unknown")
                    box = det.get("box_2d_absolute", [])
                    summary_parts.append(f"      - {label} at [{box[0]}, {box[1]}, {box[2]}, {box[3]}]")
        
        return "\n".join(summary_parts)
    
    def save_detections(self, tag_id: str, detection_data: Dict):
        """Save detection results to JSON file.
        
        Args:
            tag_id: ID of the tag
            detection_data: Detection data to save
        """
        output_file = self.detections_dir / f"{tag_id}_detections.json"
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(detection_data, f, indent=2)
            print(f"  💾 Saved detections to: {output_file}")
        except Exception as e:
            print(f"  ❌ Error saving detections: {e}")
    
    def save_summary(self, tag_id: str, summary: str):
        """Save summary text to file.
        
        Args:
            tag_id: ID of the tag
            summary: Summary text to save
        """
        output_file = self.detections_dir / f"{tag_id}_summary.txt"
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"  📄 Saved summary to: {output_file}")
        except Exception as e:
            print(f"  ❌ Error saving summary: {e}")
    
    def process_all_tags(self, tag_id: Optional[str] = None):
        """Process evidence images for tags.
        
        Args:
            tag_id: Specific tag ID to process. If None, processes all tags.
        """
        # Load tags
        self.tag_manager.load()
        
        if not self.tag_manager.tags:
            print("❌ No tags found. Create some tags first.")
            return
        
        # Determine which tags to process
        if tag_id:
            tag = self.tag_manager.get_tag_by_id(tag_id)
            if not tag:
                print(f"❌ Tag with ID '{tag_id}' not found.")
                return
            tags_to_process = [tag]
        else:
            tags_to_process = self.tag_manager.tags
        
        print(f"\n🚀 Starting evidence processing for {len(tags_to_process)} tag(s)...")
        print("=" * 60)
        
        # Process each tag
        for tag in tags_to_process:
            try:
                # Process tag photos
                detection_data = self.process_tag_photos(tag)
                
                # Save results
                self.save_detections(tag.id, detection_data)
                self.save_summary(tag.id, detection_data["summary"])
                
                # Print summary
                print(f"\n📊 Summary for '{tag.title}':")
                total_detections = detection_data.get('total_detections', 0)
                detected_objects = detection_data.get('detected_objects', [])
                print(f"   Objects detected: {total_detections}")
                print(f"   Unique types: {len(detected_objects)}")
                if detected_objects:
                    print(f"   Types: {', '.join(detected_objects[:5])}")
                    if len(detected_objects) > 5:
                        print(f"   ... and {len(detected_objects) - 5} more")
                
            except Exception as e:
                print(f"❌ Error processing tag '{tag.title}': {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("✅ Evidence processing complete!")
        print(f"   Results saved to: {self.detections_dir}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process evidence images using Google Gemini API"
    )
    parser.add_argument(
        "--tag-id",
        type=str,
        help="Process only a specific tag by ID"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Google Gemini API key (or set GOOGLE_API_KEY environment variable)"
    )
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = EvidenceProcessor(api_key=args.api_key)
    
    # Process tags
    processor.process_all_tags(tag_id=args.tag_id)


if __name__ == "__main__":
    main()

