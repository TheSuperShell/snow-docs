from dataclasses import dataclass
from enum import Enum
from bs4 import BeautifulSoup
from typing import Annotated
import rich
import typer
from urllib.parse import quote_plus
import requests
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt


app = typer.Typer(name="Snowflake documentation CLI")


@app.command("open", help="Open the main Snowflake documentaion page")
def open_main_documnetaion_page() -> None:
    typer.launch("https://docs.snowflake.com")
    rich.print("[green]Success![/green]")
    typer.Exit()


class LinkType(str, Enum):
    doc = "Documentation"
    knowledge_base = "Knowledge Base"


class LinkTypeOptions(str, Enum):
    doc = "doc"
    knowledge_base = "k_base"
    both = "both"


@dataclass(frozen=True, slots=True)
class Link:
    text: str
    link: str
    link_type: LinkType


@app.command("search", help="Search for a specific Snowflake topic")
def search(
    prompt: Annotated[
        list[str], typer.Argument(help="Search prompt to find the Snowflake topic")
    ],
    filter: Annotated[
        LinkTypeOptions,
        typer.Option(
            "-f", "--filter", help="filter out only specified type of documentation"
        ),
    ] = LinkTypeOptions.both,
) -> typer.Exit:
    prompt_text = " ".join(prompt)
    safe_prompt = quote_plus(prompt_text)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Loading...")
        response = requests.get(f"https://docs.snowflake.com/search?q={safe_prompt}")
    soup = BeautifulSoup(response.text, "html.parser")
    links_html = soup.find_all("a", {"class": "text-link cursor-pointer"})
    links: list[Link] = []
    rich.print("[bold blue]Choose the topic[/bold blue]")
    for i, link in enumerate(links_html):
        link_span = link.find("span")
        if link_span is None:
            rich.print("[red bold]ERROR[/red bold]")
            return typer.Exit(1)
        link_text = link_span.get_text()
        link_href = link.get("href")
        if not isinstance(link_href, str):
            rich.print("[red bold]ERROR[/red bold]")
            return typer.Exit(1)
        link_type = link.find("div", {"class": "text-xs mt-1 text-green"})
        if link_type is None:
            rich.print("[red bold]ERROR[/red bold]")
            return typer.Exit(1)
        link_type = LinkType(link_type.get_text())
        if filter != LinkTypeOptions.both and link_type.name != filter.name:
            continue
        links.append(Link(link_text, link_href, link_type))
    for i, link in enumerate(links):
        rich.print(f"{i + 1}. {link.text} -> [green]{link.link_type.value}[/green]")
    rich.print(f"{len(links) + 1}. Cancel")
    chosen_link = (
        int(
            Prompt().ask(
                "Enter the number",
                choices=[str(i + 1) for i in range(len(links) + 1)],
                show_choices=False,
            )
        )
        - 1
    )
    if chosen_link == len(links):
        rich.print("[red]Canceled[/red]")
        return typer.Exit()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]")) as progress:
        progress.add_task("Opening...")
        typer.launch(links[chosen_link].link)
    rich.print("[green]Opened[/green]")
    return typer.Exit()
