import base64
import os
import uuid
from uuid import UUID

import cloudinary.uploader
from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from loguru import logger

from core_apps.common import telemetry as bank_telemetry


def _store_image(profile_id: str, field_name: str, content: bytes) -> tuple[str, str]:
    """Cloudinary when credentials are configured, otherwise local media storage served by nginx under /media/.

    Without this fallback a profile can never become "complete" on a machine without Cloudinary credentials,
    so no bank account could ever be opened.
    """
    if settings.CLOUDINARY_ENABLED:
        response = cloudinary.uploader.upload(content)
        return response["public_id"], response["url"]
    relative = f"profiles/{profile_id}/{field_name}-{uuid.uuid4().hex[:8]}.jpg"
    saved = default_storage.save(relative, ContentFile(content))
    return saved, f"{settings.MEDIA_PUBLIC_URL}{settings.MEDIA_URL}{saved}"


@shared_task(name="upload_photos_to_cloudinary")
def upload_photos_to_cloudinary(profile_id: UUID, photos: dict) -> None:
    with bank_telemetry.span("bank.profile.upload_photos", profile_id=str(profile_id), photos=len(photos)):
        try:
            profile_model = apps.get_model("user_profile", "Profile")
            profile = profile_model.objects.select_related("user").get(id=profile_id)

            for field_name, photo_data in photos.items():
                if photo_data["type"] == "base64":
                    content = base64.b64decode(photo_data["data"])
                else:
                    # the original read photo_data["data"] here, a key that only exists for the base64 case
                    with open(photo_data["path"], "rb") as image_file:
                        content = image_file.read()
                    default_storage.delete(os.path.relpath(photo_data["path"], settings.MEDIA_ROOT))

                public_id, url = _store_image(str(profile.id), field_name, content)
                setattr(profile, field_name, public_id)
                setattr(profile, f"{field_name}_url", url)

            profile.save()
            logger.info(f"Photos for {profile.user.email} uploaded successfully")

            # Photos arrive after the profile PATCH returned: this is the moment the profile may become complete.
            from core_apps.accounts.utils import open_account_if_profile_complete

            account = open_account_if_profile_complete(profile)
            if account:
                logger.info(f"Bank account {account.account_number} opened for {profile.user.email}")
        except Exception as e:
            logger.error(f"Failed to upload photos for profile {profile_id}: {str(e)} ")
            for photo_data in photos.values():
                if photo_data["type"] == "file":
                    try:
                        os.remove(photo_data["path"])
                    except OSError:
                        pass
