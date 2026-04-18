# -*- coding: utf-8 -*-
from dataclasses import dataclass


@dataclass
class RawExtraction:
    """
    Raw data extracted from a single popup before parsing.
    Bundles text + image together so pipeline doesn't need model_copy().
    """
    raw_text: str
    image_url: str
