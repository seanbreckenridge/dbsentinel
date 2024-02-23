import io
import json
import time
import shutil
import atexit
from typing import cast
from pathlib import Path
from urllib.parse import urlparse
from functools import cache

import backoff
import httpx
import boto3  # type: ignore[import]
import pickledb  # type: ignore[import]

from mal_id.paths import image_data
from mal_id.log import logger
from app.settings import settings

client = boto3.client(
    "s3",
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
)

AUTO_DUMP = settings.IMAGE_CACHE_AUTO_DUMP


def setup_db() -> pickledb.PickleDB:
    backup = f"{image_data}.bak"
    try:
        pdb = pickledb.load(image_data, auto_dump=AUTO_DUMP)
    except Exception:
        assert Path(backup).exists()
        logger.warning(
            f"image_proxy: failed to load {image_data}, restoring from backup"
        )
        shutil.copy(backup, image_data)
        pdb = pickledb.load(image_data, auto_dump=AUTO_DUMP)

    Path(backup).write_text(json.dumps(pdb.db))

    if not AUTO_DUMP:
        atexit.register(lambda: cast(object, pdb.dump()))

    logger.info(
        f"image_proxy: loaded {len(pdb.db)} entries from {image_data} {AUTO_DUMP=} "
    )
    return pdb


@cache
def image_db() -> pickledb.PickleDB:
    return setup_db()


def _prefix_url(path: str) -> str:
    return f"{settings.S3_URL_PREFIX}/{path}"


@backoff.on_exception(backoff.expo, httpx.HTTPError, max_tries=3)
async def _get_image_bytes(url: str) -> bytes | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 404:
            logger.warning(f"image_proxy: got 404 for {url}")
            return None
        elif resp.status_code == 429:
            logger.warning(f"image_proxy: got 429 for {url}")
            time.sleep(15)
            return await _get_image_bytes(url)
        resp.raise_for_status()
        return resp.content


async def proxy_image(url: str) -> str | None:
    db = image_db()
    img_key = urlparse(url).path

    content_type: str
    if db.exists(img_key):
        resp = db.get(img_key)
        if resp == 404:
            return None
        assert isinstance(resp, str)
        return _prefix_url(resp)
    else:
        logger.info(f"image_proxy: uploading {url}")
        path = urlparse(url).path
        ext = Path(path).suffix.strip(".")

        match ext:
            case "jpeg" | "jpg":
                content_type = "image/jpg"
            case "webp":
                content_type = "image/webp"
            case "png":
                content_type = "image/png"
            case _:
                raise ValueError(f"unknown extension {ext}")

        # download image to memory
        image_bytes = await _get_image_bytes(url)
        if image_bytes is None:
            db.set(img_key, 404)
            return None

        # slugify path
        key = path.replace("/", "_").lstrip("_")

        # upload to aws s3
        client.upload_fileobj(
            io.BytesIO(image_bytes),
            Bucket=settings.S3_BUCKET,
            Key=key,
            ExtraArgs={"ContentType": content_type},
        )

        assert db.set(img_key, key)
        https_url = _prefix_url(key)
        logger.info(f"image_proxy: uploaded to {https_url}")

        return https_url
