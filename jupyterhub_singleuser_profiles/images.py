import os
import yaml
import logging
import json
from distutils.util import strtobool
from pydantic import BaseModel
from typing import List, Optional

_LOGGER = logging.getLogger(__name__)
IMAGE_LABEL = 'opendatahub.io/notebook-image'
DEFAULT_IMAGE_ANNOTATION = 'opendatahub.io/default-image'
DESCRIPTION_ANNOTATION = 'opendatahub.io/notebook-image-desc'
DISPLAY_NAME_ANNOTATION = 'opendatahub.io/notebook-image-name'
URL_ANNOTATION = 'opendatahub.io/notebook-image-url'
SOFTWARE_ANNOTATION = 'opendatahub.io/notebook-software'
DEPENDENCIES_ANNOTATION = 'opendatahub.io/notebook-python-dependencies'


class NameVersionPair(BaseModel):
    name: str
    version: str

class ImageTagInfo(BaseModel):
    software: Optional[List[NameVersionPair]]
    dependencies: Optional[List[NameVersionPair]]

class ImageInfo(BaseModel):
    description: Optional[str]
    url: Optional[str]
    display_name: Optional[str]
    name: str
    content: ImageTagInfo
    default: bool = False

class Images(object):
    def __init__(self, openshift, namespace):
        self.openshift = openshift
        self.namespace = namespace

    def get_default(self):
        image_list = self.load()

        for image in image_list:
            if image.default:
                return image.name

        return image_list[0].name if len(image_list) else None

    def tag_exists(self, tag_name, imagestream):
        """
        Check that tag_name exists in .status.tags. This handles situations where the tag exists but .spec.tags[] does not.
        """
        imagestream_status_tags = imagestream.status.get('tags', [])
        for tag in imagestream_status_tags:
            if tag_name == tag.tag:
                return True

        return False

    def load(self):
        result = []
        imagestream_list = self.openshift.get_imagestreams(IMAGE_LABEL+'=true')

        for i in imagestream_list.items:
            annotations = {}
            if i.metadata.annotations:
                annotations = i.metadata.annotations
            imagestream_tags = []
            if i.spec.tags:
                imagestream_tags = i.spec.tags

            for tag in imagestream_tags:
                if not self.tag_exists(tag.name, i):
                    continue

                tag_annotations = {}
                if tag.annotations:
                    tag_annotations = tag.annotations

                # Default name if there is no display name annotation
                imagestream_name = "%s:%s" % (i.metadata.name, tag.name)

                result.append(ImageInfo(description=annotations.get(DESCRIPTION_ANNOTATION),
                                    url=annotations.get(URL_ANNOTATION),
                                    display_name=annotations.get(DISPLAY_NAME_ANNOTATION) or imagestream_name,
                                    name=imagestream_name,
                                    content=ImageTagInfo(
                                        software=json.loads(tag_annotations.get(SOFTWARE_ANNOTATION, "[]")),\
                                        dependencies=json.loads(tag_annotations.get(DEPENDENCIES_ANNOTATION, "[]"))
                                    ),
                                    default=bool(strtobool(annotations.get(DEFAULT_IMAGE_ANNOTATION, "False")))
                                    ))

        result.sort(key=self.check_place)

        return result

    def get(self):
        result = self.load()

        return [x.dict() for x in result]
