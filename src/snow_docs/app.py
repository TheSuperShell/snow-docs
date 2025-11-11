from dataclasses import dataclass
from enum import Enum
import urllib.request
from bs4 import BeautifulSoup
from typing import Annotated
import rich
import typer
from urllib.parse import quote_plus
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
    page_size: Annotated[int, typer.Option("--page-size", help="search page size")] = 5,
) -> typer.Exit:
    prompt_text = " ".join(prompt)
    safe_prompt = quote_plus(prompt_text)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Loading...")
        req = urllib.request.Request(
            f"https://docs.snowflake.com/search?q={safe_prompt}&limit=100", method="GET"
        )
        with urllib.request.urlopen(req) as response:
            html: str = response.read()
    soup = BeautifulSoup(html, "html.parser")
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
        link_type_div = link.find("div", {"class": "text-xs mt-1 text-green"})
        if link_type_div is None:
            rich.print("[red bold]ERROR[/red bold]")
            return typer.Exit(1)
        link_type = LinkType(link_type_div.get_text())
        if filter != LinkTypeOptions.both and link_type.name != filter.name:
            continue
        links.append(Link(link_text, link_href, link_type))
    limits: tuple[int, int] = 0, page_size
    while True:
        _display_page(limits, links)
        result = _parse_prompt(limits, page_size, len(links))
        if result.cancel:
            rich.print("[red]Canceled")
            return typer.Exit()
        if result.limits != limits:
            limits = result.limits
            continue
        if result.reason is None:
            break
        rich.print(result.reason)
    typer.launch(links[result.num].link)
    rich.print("[green]Opened[/green]")
    return typer.Exit()


def _display_page(limits: tuple[int, int], search_results: list[Link]) -> None:
    for i, li in enumerate(search_results[limits[0] : limits[1]]):
        ind: int = i + limits[0]
        rich.print(f"{ind + 1}. {li.text} -> [green]{li.link_type.value}[/green]")
    rich.print(
        f"{limits[0]}-{limits[1] if limits[1] <= len(search_results) else len(search_results)} out of {len(search_results)}"
    )
    rich.print()
    if limits[1] < len(search_results):
        rich.print("type `more` to see more results")
    if limits[0] != 0:
        rich.print("type `back` to see previous page")
    rich.print("type `cancel` to [red]cancel")


@dataclass(frozen=True, slots=True)
class PromptResult:
    limits: tuple[int, int]
    num: int = 0
    reason: str | None = None
    cancel: bool = False


def _parse_prompt(
    limits: tuple[int, int], page_size: int, result_len: int
) -> PromptResult:
    prompt = Prompt.ask("Enter the number").lower()
    if prompt == "cancel":
        return PromptResult(limits, cancel=True)
    if prompt == "more":
        if limits[1] + page_size > result_len:
            return PromptResult(limits, reason="this is the last page")
        return PromptResult((limits[0] + page_size, limits[1] + page_size))
    if prompt == "back":
        if limits[0] == 0:
            return PromptResult(limits, reason="cannot go back")
        return PromptResult((limits[0] - page_size, limits[1] - page_size))
    try:
        num = int(prompt)
    except ValueError:
        return PromptResult(limits, reason=f"unkown command {prompt}")
    if num < limits[0] or num > limits[1] or num > result_len:
        return PromptResult(limits, reason="please specify the correct number")
    return PromptResult(limits, num=num - 1)
