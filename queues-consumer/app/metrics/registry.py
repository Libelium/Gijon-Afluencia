"""
Thin wrappers around prometheus_client constructors that apply a consistent
namespace prefix to every metric registered in this service.

All collectors must use these factories instead of importing directly from
prometheus_client, so the prefix is enforced in a single place.
"""

from prometheus_client import Counter, Gauge, Histogram, Summary

PREFIX = "pidgijon"


def _name(metric_name: str) -> str:
    return f"{PREFIX}_{metric_name}"


def counter(name: str, documentation: str, labelnames: list[str] = ()) -> Counter:
    return Counter(_name(name), documentation, labelnames)


def gauge(name: str, documentation: str, labelnames: list[str] = ()) -> Gauge:
    return Gauge(_name(name), documentation, labelnames)


def histogram(name: str, documentation: str, labelnames: list[str] = ()) -> Histogram:
    return Histogram(_name(name), documentation, labelnames)


def summary(name: str, documentation: str, labelnames: list[str] = ()) -> Summary:
    return Summary(_name(name), documentation, labelnames)
