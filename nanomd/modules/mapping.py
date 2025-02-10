import typer
import subprocess
from pathlib import Path
from rich.progress import track
from typing_extensions import Annotated
from ..utils.map import minimap2map

app = typer.Typer()

@app.callback()
def callback():
    """
    nanomd is a package for analyzing nanopore RNA sequencing data.
    """

@app.command()
def mapping(
    input: Annotated[str, typer.Option("--input", "-i", help="Input fastq files.")],
    reference: Annotated[str, typer.Option("--reference", "-r", help="reference genome path.")],
    prefix: Annotated[str, typer.Option("--prefix", "-p", help="Prefix for output files.")],
    tool: Annotated[str, typer.Option("--tool", help="minimap2.")]="minimap2",
    parms: Annotated[str, typer.Option("--parms", help="minimap2 parameters for mapping.")]="--secondary=no --cs -a",
    threads: Annotated[int, typer.Option(help="Number of threads.")]=4,
    ):
    """
    Mapping of nanopore reads to a reference genome.
    """
    minimap2map(input, reference, prefix, tool, parms, threads)