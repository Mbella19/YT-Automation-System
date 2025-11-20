import os
import json
from google import genai
from PIL import Image
from io import BytesIO
from rembg import remove

class GeminiService:
    """Service for Google Gemini API integration"""
    
    def __init__(self, api_key):
        """Initialize Gemini API with key"""
        if not api_key:
            raise ValueError("Google API key is required")
        
        os.environ['GOOGLE_API_KEY'] = api_key
        self.client = genai.Client(api_key=api_key)
    
    def virtual_tryon(self, person_image_path, clothing_image_paths, prompt="try on clothes"):
        """
        Generate virtual try-on using Gemini 2.5 Flash Image Generation
        
        Args:
            person_image_path: Path to user's photo
            clothing_image_paths: Path or list of paths to clothing item images
            prompt: Instruction prompt for Gemini
            
        Returns:
            Generated image as PIL Image object
        """
        try:
            # Load images
            person_image = Image.open(person_image_path)
            if isinstance(clothing_image_paths, (list, tuple, set)):
                clothing_images = [Image.open(path) for path in clothing_image_paths]
            else:
                clothing_images = [Image.open(clothing_image_paths)]
            
            print(f"🤖 Generating virtual try-on with Gemini...")
            print(f"Person image: {person_image.size}")
            for idx, img in enumerate(clothing_images, start=1):
                print(f"Clothing image {idx}: {img.size}")
            
            # Build contents payload with clothing images, person image, and prompt
            # Matching user example: Clothing first, then Person
            contents = []
            contents.extend(clothing_images)
            contents.append(person_image)
            contents.append(prompt)
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    temperature=0.5,
                    image_config=genai.types.ImageConfig(
                        aspect_ratio="9:16"
                    )
                )
            )
            
            # Extract generated image from response
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(f"✓ Gemini response: {part.text[:100]}...")
                    self.last_analysis = part.text
                elif part.inline_data is not None:
                    # Decode the generated image
                    print("✓ Image generated successfully!")
                    image = Image.open(BytesIO(part.inline_data.data))
                    return image
            
            # If no image was generated, create preview
            print("⚠️  No image in response, creating preview...")
            return self._create_preview_image(person_image, clothing_images[0])
            
        except Exception as e:
            print(f"❌ Error in virtual try-on: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Virtual try-on failed: {str(e)}")
    
    def _create_preview_image(self, person_image, clothing_image):
        """Create a simple preview by combining images (fallback)"""
        # Resize images to same height
        target_height = 600
        
        person_ratio = target_height / person_image.height
        person_width = int(person_image.width * person_ratio)
        person_resized = person_image.resize((person_width, target_height), Image.Resampling.LANCZOS)
        
        clothing_ratio = target_height / clothing_image.height
        clothing_width = int(clothing_image.width * clothing_ratio)
        clothing_resized = clothing_image.resize((clothing_width, target_height), Image.Resampling.LANCZOS)
        
        # Create combined image
        total_width = person_width + clothing_width
        combined = Image.new('RGB', (total_width, target_height), (255, 255, 255))
        combined.paste(person_resized, (0, 0))
        combined.paste(clothing_resized, (person_width, 0))
        
        return combined

    def recommend_outfits(self, styling_context):
        """
        Use Gemini 2.5 Flash to recommend outfits based on provided context.
        
        Args:
            styling_context: String prompt describing occasion, wardrobe, and constraints.
            
        Returns:
            Parsed JSON response with outfit recommendations.
        """
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=styling_context
            )
            
            raw_text = getattr(response, 'text', None)
            
            if not raw_text and getattr(response, 'candidates', None):
                aggregated = []
                for candidate in response.candidates:
                    content = getattr(candidate, 'content', None)
                    if not content:
                        continue
                    for part in getattr(content, 'parts', []):
                        text = getattr(part, 'text', None)
                        if text:
                            aggregated.append(text)
                if aggregated:
                    raw_text = "\n".join(aggregated)
            
            if not raw_text:
                raise ValueError("Gemini returned no text content for outfit recommendations")
            
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                segments = cleaned.split("```")
                # segments: ["", "json\n{...}", ""]
                for segment in segments:
                    segment = segment.strip()
                    if not segment:
                        continue
                    if segment.lower().startswith("json"):
                        cleaned = segment.split("\n", 1)[1] if "\n" in segment else ""
                        break
                    cleaned = segment
            
            return json.loads(cleaned)
        
        except json.JSONDecodeError as exc:
            print(f"❌ Failed to parse Gemini response as JSON: {exc}")
            raise ValueError("Unable to parse outfit recommendations response") from exc
        except Exception as exc:
            print(f"❌ Error requesting outfit recommendations: {exc}")
            raise

    def generate_clothing_image(self, description):
        """
        Generate a clothing image from text description using Gemini.
        
        Args:
            description: Text description of the clothing item
            
        Returns:
            Generated image as PIL Image object
        """
        try:
            prompt = f"A professional, clean, flat-lay product photography of {description} on a pure white background. High quality, realistic texture, studio lighting. Ensure the item is isolated."
            
            print(f"🎨 Generating clothing image for: {description}")
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.5,
                    image_config=genai.types.ImageConfig(
                        aspect_ratio="1:1"
                    )
                )
            )
            
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    print("✓ Clothing image generated successfully!")
                    img = Image.open(BytesIO(part.inline_data.data))
                    
                    # Remove background to ensure transparency
                    print("✨ Removing background from generated image...")
                    return remove(img)
            
            raise Exception("No image generated")
            
        except Exception as e:
            print(f"❌ Error generating clothing image: {str(e)}")
            raise
    
    def refine_clothing_image(self, image_path, refinement_prompt):
        """
        Refine a generated clothing image based on user prompt.
        
        Args:
            image_path: Path to the previous image
            refinement_prompt: User's instruction for changes
            
        Returns:
            Refined image as PIL Image object
        """
        try:
            # Load previous image
            previous_image = Image.open(image_path)
            
            # Construct prompt
            prompt = f"Edit this clothing item. {refinement_prompt}. Keep the item isolated on a pure white background. High quality, realistic texture."
            
            print(f"🎨 Refining clothing image with prompt: {refinement_prompt}")
            
            contents = [prompt, previous_image]
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    temperature=0.5
                )
            )
            
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    print("✓ Refined image generated successfully!")
                    img = Image.open(BytesIO(part.inline_data.data))
                    
                    # Remove background
                    print("✨ Removing background from refined image...")
                    return remove(img)
            
            raise Exception("No image generated during refinement")
            
        except Exception as e:
            print(f"❌ Error refining clothing image: {str(e)}")
            raise Exception("No image generated")
            
        except Exception as e:
            print(f"❌ Error generating clothing image: {str(e)}")
            raise
