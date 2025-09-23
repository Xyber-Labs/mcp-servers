import asyncio
import base64
import logging
import os
from pathlib import Path
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Any, Literal
from pydantic import BaseModel, Field


# --- Experiment Configuration --- #
class ExperimentSettings(BaseModel):
    """Defines the settings for a single image generation experiment."""

    # Server configuration
    server_url: str = "https://dev.ai-mcp-stability.ent-dx.com/mcp-server/mcp/"
    service_name: str = "stability"

    # Generation parameters
    prompts: list[str]
    negative_prompt: str | None
    aspect_ratio: str
    seed: int
    style_preset: Literal[
        "3d-model",
        "analog-film",
        "anime",
        "cinematic",
        "comic-book",
        "digital-art",
        "enhance",
        "fantasy-art",
        "isometric",
        "line-art",
        "low-poly",
        "modeling-compound",
        "neon-punk",
        "origami",
        "photographic",
        "pixel-art",
        "tile-texture",
    ] | None

    # Output configuration
    output_dir: str


# --- Basic logging setup --- #
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("mcp-client")


class ImageGenerationClient:
    """A client to interact with the MCP image generation server."""

    def __init__(self, settings: ExperimentSettings):
        """Initializes the client with the given settings."""
        self.settings = settings
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.mcp_client = MultiServerMCPClient(
            {
                settings.service_name: {
                    "url": settings.server_url,
                    "transport": "streamable_http",
                }
            }
        )

    async def _generate_and_save_image(
        self, pbar: Progress, task_id, prompt_text: str, prompt_index: int
    ) -> None:
        """Generates a single image and saves it to the output directory."""
        request_params = {
            "prompt": prompt_text,
            "negative_prompt": self.settings.negative_prompt,
            "aspect_ratio": self.settings.aspect_ratio,
            "seed": self.settings.seed + prompt_index,
            "style_preset": self.settings.style_preset,
        }

        try:
            pbar.update(task_id, description=f"Generating image {prompt_index + 1}...")
            tools = await self.mcp_client.get_tools()
            response = await tools[0].ainvoke(input={"request": request_params})
            image_data = base64.b64decode(response)
            image_path = self.output_dir / f"generated_image_{prompt_index + 1}.png"
            with open(image_path, "wb") as f:
                f.write(image_data)

            pbar.update(
                task_id,
                advance=1,
                description=f"Image {prompt_index + 1} saved to {image_path}",
            )
        except Exception as e:
            logger.error(f"Error generating image {prompt_index + 1}: {e}")
            pbar.update(task_id, advance=1)  # Still advance to not stall the progress

    async def run(self) -> None:
        """Runs the image generation process for the configured number of images."""
        logger.info(
            f"Starting image generation process for {len(self.settings.prompts)} prompts..."
        )
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as pbar:
            generation_task = pbar.add_task(
                "Generating images", total=len(self.settings.prompts)
            )
            tasks = [
                self._generate_and_save_image(pbar, generation_task, prompt_text, i)
                for i, prompt_text in enumerate(self.settings.prompts)
            ]
            await asyncio.gather(*tasks)

        logger.info("Image generation process completed.")


async def run_experiment(params: dict[str, Any]) -> None:
    """Runs a single experiment with the given parameters."""
    settings = ExperimentSettings(**params)
    logger.info("Loaded client settings:")
    logger.info(f"  - Server URL: {settings.server_url}")
    logger.info(f"  - Service Name: {settings.service_name}")
    logger.info(f"  - Number of prompts: {len(settings.prompts)}")
    for idx, prompt in enumerate(settings.prompts, start=1):
        logger.info(f"    {idx}. {prompt}")
    logger.info(f"  - Output directory: '{settings.output_dir}'")

    client = ImageGenerationClient(settings)
    await client.run()


async def main() -> None:
    """Main function to run the client."""
    # Experiment 1: Baseline with neon-punk style
    await run_experiment(
        {
            "prompts": [
                "A futuristic cyberpunk room with neon lights, holographic displays, and advanced technology. The room is empty, with no people. The style is sleek and modern, with a focus on glowing elements and a dark, atmospheric mood.",
                "A neon-soaked rainforest at night with bioluminescent plants and holographic fireflies shimmering between trees, cinematic and moody.",
                "A cybernetic bonsai garden floating on a glass platform, roots entwined with glowing circuits and tiny drones pruning leaves.",
                "An abandoned arcade alley where retro cabinets hum with neon life, rain-slick pavement reflecting saturated colors, no people.",
            ],
            "negative_prompt": "person, human, people, blurry, noisy, ugly, deformed",
            "style_preset": "neon-punk",
            "output_dir": "exp1",
            "seed": 123,
            "aspect_ratio": "16:9",
        }
    )

    # Experiment 2: Refined prompt with photographic style
    await run_experiment(
        {
            "prompts": [
                "An empty, futuristic room with a sleek, minimalist design. The room is illuminated by soft, ambient neon lights in shades of blue and purple. A large holographic interface displays glowing data streams. The surfaces are reflective, and the overall atmosphere is clean, high-tech, and serene.",
                "An empty airport terminal at dawn with golden light streaking across polished floors, realistic reflections, ultra sharp.",
                "A minimalist tea house with concrete, glass, and a single bonsai framed by a window of misty mountains, natural light.",
                "A deserted coastal boardwalk at blue hour, wet planks reflecting pier lights, photorealistic and quiet, no people.",
            ],
            "negative_prompt": "person, human, people, blurry, noisy, ugly, deformed, cluttered, messy",
            "style_preset": "photographic",
            "output_dir": "exp2",
            "seed": 456,
            "aspect_ratio": "16:9",
        }
    )

    # Experiment 3: Cinematic style with a detailed prompt
    await run_experiment(
        {
            "prompts": [
                "A vast, empty server room with rows of glowing racks. The lighting is dramatic, with shafts of light cutting through the darkness. The air is filled with a light haze, and the overall mood is one of mystery and immense scale. The style is cinematic, with a focus on depth and atmosphere.",
                "An alien desert city seen from a balcony at sunset, colossal arches casting long shadows, sand caught in orange light.",
                "A lighthouse control room during a storm, beams of light rotating and rain streaking across porthole glass, atmospheric and moody.",
                "An ancient library with floating holographic scrolls between marble columns, shafts of dust-lit light, epic scale.",
            ],
            "negative_prompt": "person, human, people, blurry, noisy, ugly, deformed, cluttered, messy",
            "style_preset": "cinematic",
            "output_dir": "exp3",
            "seed": 789,
            "aspect_ratio": "16:9",
        }
    )

    # Experiment 4: Cinematic style with a focus on lighting and detail
    await run_experiment(
        {
            "prompts": [
                "A hyper-realistic, empty data center with racks of servers casting long shadows. The primary light source is the cool, blue glow from the server LEDs, with occasional bursts of orange and red from status indicators. The camera angle is low, emphasizing the scale of the room. The style is cinematic, with a shallow depth of field and a strong sense of realism.",
                "An art gallery of polished concrete at night lit by a single skylight, spotlit sculptures casting dramatic shadows.",
                "An empty train platform at midnight drenched in tungsten and cyan, fog rolling through pools of light, cinematic bokeh.",
                "A cathedral-sized ice cave with luminescent blue walls and a beam of sunlight cutting through ice dust.",
            ],
            "negative_prompt": "person, human, people, blurry, noisy, ugly, deformed, cluttered, messy, cartoon, drawing, painting",
            "style_preset": "cinematic",
            "output_dir": "exp4",
            "seed": 101,
            "aspect_ratio": "16:9",
        }
    )

    # Experiment 5: Futuristic virtual marketplace
    await run_experiment(
        {
            "prompts": [
                "An empty, futuristic virtual marketplace with holographic stalls and neon signs. The air is filled with glowing data streams and floating icons. The style is cinematic and high-tech, with a focus on vibrant colors and a bustling, yet unpopulated, atmosphere.",
                "A zero-gravity greenhouse with floating droplets of water and vine trellises rotated 90 degrees, glowing grow lights.",
                "An underwater research corridor with glass walls revealing bioluminescent fish trails, cool cyan palette, no people.",
                "A floating monolith garden above clouds, stepping stones hovering in air, thin mist, saturated sunrise.",
            ],
            "negative_prompt": "person, human, people, blurry, noisy, ugly, deformed, cluttered, messy, cartoon, drawing, painting",
            "style_preset": "cinematic",
            "output_dir": "exp5",
            "seed": 202,
            "aspect_ratio": "1:1",
        }
    )

    # Experiment 6: Bright and beautiful futuristic conference hall
    await run_experiment(
        {
            "prompts": [
                "An empty, futuristic conference hall with floor-to-ceiling windows overlooking a serene, futuristic cityscape. The room is bathed in bright, natural light, and the design is minimalist and elegant, with white and silver surfaces. The style is cinematic and beautiful, with a focus on a clean, high-tech aesthetic.",
                "A white observatory interior at sunrise, telescopes silhouetted against pink sky, glass and brushed metal, airy and bright.",
                "A minimalist kitchen with skylight beams, soft shadows across marble, plants in hydroponic columns, ultra clean.",
                "A serene museum atrium with suspended kinetic sculpture casting moving highlights on white walls.",
            ],
            "negative_prompt": "dark, gloomy, person, human, people, blurry, noisy, ugly, deformed, cluttered, messy, cartoon, drawing, painting",
            "style_preset": "cinematic",
            "output_dir": "exp6",
            "seed": 303,
            "aspect_ratio": "16:9",
        }
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user.")
