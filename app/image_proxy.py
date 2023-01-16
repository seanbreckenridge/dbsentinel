import io
import json
import time
import shutil
import atexit
from pathlib import Path
from urllib.parse import urlparse

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


def setup_db() -> pickledb.PickleDB:
    backup = f"{image_data}.bak"
    try:
        pdb = pickledb.load(image_data, auto_dump=True)
    except Exception:
        assert Path(backup).exists()
        logger.warning(
            f"image_proxy: failed to load {image_data}, restoring from backup"
        )
        shutil.copy(backup, image_data)
        pdb = pickledb.load(image_data, auto_dump=True)

    Path(backup).write_text(json.dumps(pdb.db))

    atexit.register(pdb.dump)

    logger.info(f"image_proxy: loaded {len(pdb.db)} entries from {image_data}")
    return pdb


db = setup_db()


def _prefix_url(path: str) -> str:
    return f"{settings.S3_URL_PREFIX}/{path}"


@backoff.on_exception(backoff.expo, httpx.HTTPError, max_tries=3)
def _get_image_bytes(url: str) -> bytes | None:
    with httpx.Client() as client:
        resp = client.get(url)
        if resp.status_code == 404:
            logger.warning(f"image_proxy: got 404 for {url}")
            return None
        elif resp.status_code == 429:
            logger.warning(f"image_proxy: got 429 for {url}")
            time.sleep(15)
            return _get_image_bytes(url)
        resp.raise_for_status()
        return resp.content


def proxy_image(url: str) -> str | None:
    if db.exists(url):
        resp = db.get(url)
        if resp == 404:
            return None
        assert isinstance(resp, str)
        return _prefix_url(resp)
    else:
        logger.info(f"image_proxy: uploading {url}")
        path = urlparse(url).path
        ext = Path(path).suffix.strip(".")
        assert ext in {"jpeg", "jpg"}

        # download image to memory
        image_bytes = _get_image_bytes(url)
        if image_bytes is None:
            db.set(url, 404)
            return None

        # slugify path
        key = path.replace("/", "_").lstrip("_")

        # upload to aws s3
        client.upload_fileobj(
            io.BytesIO(image_bytes),
            Bucket=settings.S3_BUCKET,
            Key=key,
            ExtraArgs={"ContentType": "image/jpg"},
        )

        assert db.set(url, key)
        https_url = _prefix_url(key)
        logger.info(f"image_proxy: uploaded to {https_url}")

        return https_url
