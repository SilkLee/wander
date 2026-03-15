from enum import Enum


class DORALevel(str, Enum):
    ELITE = "elite"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MetricInterval(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
