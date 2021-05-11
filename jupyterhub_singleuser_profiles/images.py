import os
import yaml
import logging
import json
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
IMAGE_ORDER_ANNOTATION = 'opendatahub.io/image-order'


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
    order: int = 100

class Images(object):
    def __init__(self, openshift, namespace):
        self.openshift = openshift
        self.namespace = namespace


    def get_images_legacy(self, result):
        """Kept for backwards compatibility"""

        for i in self.openshift.get_imagestreams().items:
            if '-notebook' in i.metadata.name:
                self.append_option(i, result)

    def get_default(self):
        image_list, code = self.get(detailed=False)

        if len(image_list) > 0:
            return image_list[0]

        return ''

    def tag_exists(self, tag_name, imagestream):
        for tag in imagestream.spec.tags:
            if tag_name == tag.name:
                return True

        return False

    def check_place(self, imagestream):
        return imagestream.order

    def load(self):
        result = []
        imagestream_list = self.openshift.get_imagestreams(IMAGE_LABEL+'=true')

        for i in imagestream_list.items:
            if i.metadata.name == name:
                annotations = i.metadata.annotations
                for tag in i.spec.tags:
                    if tag.name == tag_name:
                        tag_annotations = tag.annotations
                if not tag_annotations:
                    _LOGGER.error("Image tag not found!")
                    return "Image tag not found", 404

                return ImageInfo(description=annotations.get(desc),
                                    url=annotations.get(url),
                                    display_name=annotations.get(display_name),
                                    name=image_name,
                                    content=ImageTagInfo(
                                        software=json.loads(tag.annotations.get(SOFTWARE_ANNOTATION, "[]")),\
                                        dependencies=json.loads(tag.annotations.get(DEPENDENCIES_ANNOTATION, "[]"))
                                    ),
                                    default=bool(strtobool(annotations.get(DEFAULT_IMAGE_ANNOTATION, "False"))),
                                    order=int(annotations.get(IMAGE_ORDER_ANNOTATION, 100))
                                    ))

        result.sort(key=self.check_place)

        return result

    def get(self):
        result = self.load()

        return [x.dict() for x in result]
