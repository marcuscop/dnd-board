from __future__ import annotations

import argparse
from pathlib import Path

import torch
from diffusers import Flux2KleinPipeline


DEFAULT_MODEL = "black-forest-labs/FLUX.2-klein-4B"
DEFAULT_PROMPT = "siren (dungeons and dragons monster, dark fantasy art, substantial design, isolated on white background, detailed watercolor vignette)"
DEFAULT_OUTPUT = Path("flux-klein.png")
DEFAULT_SIZE = 512


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one image locally with FLUX.2 Klein 4B through Diffusers.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--height", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--width", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--guidance-scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--debug-memory", action="store_true")
    parser.add_argument("--no-vae-tiling", action="store_true")
    parser.add_argument("--no-vae-slicing", action="store_true")
    args = parser.parse_args()

    device = choose_device(args.device)
    dtype = choose_dtype(device)
    print(f"Loading {args.model} on {device} with {dtype}...")

    def mps_callback(_pipe, step_index, _timestep, callback_kwargs):
        if device == "mps" and args.debug_memory:
            torch.mps.empty_cache()
            allocated = torch.mps.current_allocated_memory() / (1024**3)
            print(f" -> Step {step_index} | MPS Allocated Memory: {allocated:.2f} GB")
        return callback_kwargs

    pipe = Flux2KleinPipeline.from_pretrained(args.model, torch_dtype=dtype)
    configure_memory_savers(pipe, vae_tiling=not args.no_vae_tiling, vae_slicing=not args.no_vae_slicing)
    if device == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(device)

    generator = torch.Generator(device=device if device == "cuda" else "cpu").manual_seed(args.seed)
    image = pipe(
        prompt=args.prompt,
        height=args.height,
        width=args.width,
        guidance_scale=args.guidance_scale,
        num_inference_steps=args.steps,
        generator=generator,
        callback_on_step_end=mps_callback,
    ).images[0]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(f"Saved: {args.output}")


def configure_memory_savers(pipe: Flux2KleinPipeline, *, vae_tiling: bool, vae_slicing: bool) -> None:
    if vae_tiling:
        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()
            print("Enabled VAE tiling")
        elif hasattr(pipe.vae, "enable_tiling"):
            pipe.vae.enable_tiling()
            print("Enabled VAE tiling")

    if vae_slicing:
        if hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()
            print("Enabled VAE slicing")
        elif hasattr(pipe.vae, "enable_slicing"):
            pipe.vae.enable_slicing()
            print("Enabled VAE slicing")


def choose_device(requested_device: str) -> str:
    if requested_device != "auto":
        return requested_device
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def choose_dtype(device: str) -> torch.dtype:
    if device == "cuda":
        return torch.bfloat16
    if device == "mps":
        return torch.float16
    return torch.float32


if __name__ == "__main__":
    main()
