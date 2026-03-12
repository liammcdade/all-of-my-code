"""Plugin modules for extended functionality."""

from .calculator import CalculatorProcessor
from .geo import GeoProcessor
from .ml import MLModel
from .sql import SQLProcessor

__all__ = ['CalculatorProcessor', 'GeoProcessor', 'MLModel', 'SQLProcessor']
