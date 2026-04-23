"""Message rendering for terminal output."""
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown


class MessageType(Enum):
    """Message type enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


console = Console()


def render_message(content: str, message_type: MessageType) -> str:
    """
    Render a message with appropriate formatting.
    
    Args:
        content: Message content
        message_type: Type of message
        
    Returns:
        Formatted message string
    """
    if message_type == MessageType.USER:
        panel = Panel(
            content,
            title="[bold blue]User[/bold blue]",
            border_style="blue",
        )
        with console.capture() as capture:
            console.print(panel)
        return capture.get()
    
    elif message_type == MessageType.ASSISTANT:
        md = Markdown(content)
        with console.capture() as capture:
            console.print(md)
        return capture.get()
    
    elif message_type == MessageType.SYSTEM:
        with console.capture() as capture:
            console.print(f"[dim]{content}[/dim]")
        return capture.get()
    
    elif message_type == MessageType.TOOL:
        panel = Panel(
            content,
            title="[bold green]Tool Result[/bold green]",
            border_style="green",
        )
        with console.capture() as capture:
            console.print(panel)
        return capture.get()
    
    return content
