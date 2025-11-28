"""
EMR to Heidi Integration - Core Module
核心功能模块，独立于任何集成方式
"""

__version__ = "1.0.0"
__author__ = "EMR-Heidi Integration Team"

from .capture import capture_emr_region, get_screen_coordinates_helper
from .ocr_parser import run_ocr, parse_patient_info
from .heidi_client import HeidiClient

__all__ = [
    "capture_emr_region",
    "get_screen_coordinates_helper",
    "run_ocr",
    "parse_patient_info",
    "HeidiClient",
]
