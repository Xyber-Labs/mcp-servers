import asyncio
import base64
import logging
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient


class ExperimentSettings:
    def __init__(
        self,
        server_url: str,
        service_name: str,
        prompts: list[str],
        output_dir: str,
        refine_prompt: bool = False,
        lora_scale: float | None = None,
    ) -> None:
        self.server_url = server_url
        self.service_name = service_name
        self.prompts = prompts
        self.output_dir = output_dir
        self.refine_prompt = refine_prompt
        self.lora_scale = lora_scale


class ImageGenerationClient:
    def __init__(self, settings: ExperimentSettings) -> None:
        self.settings = settings
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mcp_client = MultiServerMCPClient(
            {
                settings.service_name: {
                    "url": settings.server_url,
                    "transport": "streamable_http",
                }
            }
        )

    async def _generate_and_save_image(self, prompt_text: str, index: int) -> None:
        request: dict[str, Any] = {"prompt": prompt_text}
        if self.settings.refine_prompt:
            request["refine_prompt"] = True
        if self.settings.lora_scale is not None:
            request["lora_scale"] = float(self.settings.lora_scale)

        tools = await self.mcp_client.get_tools()
        response_b64: str = await tools[0].ainvoke(input={"request": request})
        image_bytes = base64.b64decode(response_b64)
        image_path = self.output_dir / f"together_image_{index + 1}.png"
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        logging.info(f"Saved: {image_path}")

    async def run(self) -> None:
        tasks = [self._generate_and_save_image(p, i) for i, p in enumerate(self.settings.prompts)]
        await asyncio.gather(*tasks)


async def run_experiment(params: dict[str, Any]) -> None:
    settings = ExperimentSettings(**params)
    logging.info("Together MCP client settings:")
    logging.info(f"  - Server URL: {settings.server_url}")
    logging.info(f"  - Service Name: {settings.service_name}")
    logging.info(f"  - Number of prompts: {len(settings.prompts)}")
    logging.info(f"  - Output directory: '{settings.output_dir}'")

    client = ImageGenerationClient(settings)
    await client.run()


async def main() -> None:
    prompts: list[str] = [
        # 1
        "A young girl with light hair in a red (#E60B40) blazer, white blouse, and dark jeans holds a receipt while gold coins scatter from a vintage cash register. Confident, curious look; boutique background, colorful and juicy, photorealistic.",
        # 2
        "A young girl with light hair in a green hoodie and black chinos at a desk, frowning thoughtfully at a document labeled 'Policy Draft'. Warm daylight, friendly office, casual realism, no neon.",
        # 3
        "A young girl with light hair in a blue blazer, grey trousers, and white sneakers presenting a rising chart on a glass board. Bright co-working space, candid smile, modern casual style.",
        # 4
        "A young girl with light hair in beige trench coat, navy knit top, and jeans checking a bill at a cafe table; thoughtful, daylight through window, soft colors, natural candid feel.",
        # 5
        "A young girl with light hair in a grey turtleneck, charcoal blazer, and black pants assembling a clear gear model on a table; focused expression, bright studio with plants, colorful accents.",
        # 6
        "A young girl with light hair in a sharp red (#E60B40) pantsuit standing by an unbalanced brass scale, pointing at notes in a notebook; minimalist courtroom hallway, bright and clean.",
        # 7
        "A young girl with light hair in denim jacket, black tee, and slate chinos comparing two documents labeled 'Markets' and 'Policy'. Sunlit office nook, plants, warm tones, casual realism.",
        # 8
        "A young girl with light hair in a cream sweater, olive blazer, and dark jeans reviewing a budget spreadsheet on a laptop; yellow highlighter and sticky notes; airy apartment desk, cozy vibe.",
        # 9
        "A young girl with light hair in a navy hoodie, light jacket, and jeans placing a coin in a clear donation box; community center background, friendly smiles on posters, bright colors.",
        # 10
        "A young girl with light hair in a white button-up, light blue cardigan, and black trousers presenting a balanced bar chart on a tablet; modern conference room, upbeat, colorful and juicy.",
    ]

    await run_experiment(
        {
            "server_url": "http://localhost:8016/mcp-server/mcp/",
            "service_name": "together",
            "prompts": prompts,
            "output_dir": "together_exp",
            "refine_prompt": True,
            "lora_scale": 0.9,
        }
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Client stopped by user.")
