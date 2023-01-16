import io
import time
from pathlib import Path
from urllib.parse import urlparse

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

db = pickledb.load(image_data, auto_dump=True)


def _prefix_url(path: str) -> str:
    return f"{settings.S3_URL_PREFIX}/{path}"


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
        with httpx.Client() as url_client:
            image_response = url_client.get(url)
            if image_response.status_code == 429:
                logger.warning(f"image_proxy: got 429 for {url}")
                time.sleep(15)
                return proxy_image(url)
            elif image_response.status_code == 404:
                logger.warning(f"image_proxy: got 404 for {url}")
                db.set(url, 404)
                return None
            if image_response.status_code != 200:
                raise Exception("could not download image")
            buf = io.BytesIO(image_response.content)

        # slugify path
        key = path.replace("/", "_").lstrip("_")

        # upload to aws s3
        client.upload_fileobj(
            buf,
            Bucket=settings.S3_BUCKET,
            Key=key,
            ExtraArgs={"ContentType": "image/jpg"},
        )

        assert db.set(url, key)
        https_url = _prefix_url(key)
        logger.info(f"image_proxy: uploaded to {https_url}")

        return https_url
