import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from resonance.config import process_environment


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parameters = StdioServerParameters(
        command=str(root / ".venv/bin/python"),
        args=[str(root / "mcp/server.py")],
        env=process_environment({"PYTHONPATH": str(root)}),
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            measured = await session.call_tool(
                "measure", {"capture_id": "demo-capture-4"}
            )
            assert not measured.isError
            content = measured.content[0]
            assert isinstance(content, TextContent)
            result = json.loads(content.text)
            assert result["outcome"] == "MEASURED"
            print(
                json.dumps(
                    {
                        "tools": [tool.name for tool in tools.tools],
                        "measurement_outcome": result["outcome"],
                    }
                )
            )


if __name__ == "__main__":
    asyncio.run(main())
