import argparse
import asyncio
import json

import httpx


async def main(output_location):
    url = "https://raw.githubusercontent.com/Netflix-Skunkworks/policyuniverse/master/policyuniverse/data.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

    # Extract the service names
    service_names = list(set([data[name]["prefix"].lower() for name in data.keys()]))

    # Sort the service names in alphabetical order
    service_names.sort()

    assert len(service_names) >= 350  # Sanity check

    # Write the service names to a JSON file
    with open(output_location, "w") as f:
        json.dump(service_names, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and parse AWS service names."
    )
    parser.add_argument(
        "--output_location",
        default="service_names.json",
        help="Output location for the service names.",
    )
    args = parser.parse_args()

    asyncio.run(main(args.output_location))
