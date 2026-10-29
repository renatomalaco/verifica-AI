"""Entry point of the egress proxy container: python -m url_inspector.egress"""

import asyncio
import logging

from url_inspector.infrastructure.egress_proxy import serve

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
