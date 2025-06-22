from mcp.server.fastmcp import FastMCP

# Create an MCP server with a custom name
mcp = FastMCP("Opentrons Server")


@mcp.tool()
def get_available_pipettes() -> list[tuple[str, str]]:
    """
    Returns a list of available pipettes that are currently available to be used on the Opentrons
    Returns the name of the pipette and the current location "left" or "right" as a tuple: (name, location)
    """
    return [("flex_1channel_1000", "left")]


@mcp.tool()
def get_available_resources() -> list[tuple[str, str, str]]:
    """
    Returns a list of resources that are currently on the Opentrons
    Returns the name of the type, name, and nest location resource: (type, name, nest_location)
    """
    return [
        ("pipette_tips", "opentrons_flex_96_tiprack_200ul", "D1"),
        ("reservoir", "nest_12_reservoir_15ml", "D2"),
        ("plate", "nest_96_wellplate_200ul_flat", "D3"),
        ("trash", "trash", "A3"),
    ]


@mcp.tool()
def generate_protocol(
    steps: list[str],
    pipettes: list[tuple[str, str]],
    resources: list[tuple[str, str, str]],
) -> str:
    return "print('nice')"


if __name__ == "__main__":
    mcp.run()
