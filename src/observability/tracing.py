from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
import os

_initialized = False

def init_tracer(service_name: str = "clinicaltrial-ai") -> None:
    global _initialized
    if _initialized:
        return
    enable = os.getenv("OTEL_ENABLE", "true").lower() in ("1","true","yes")
    if not enable:
        _initialized = True
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = ConsoleSpanExporter()
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _initialized = True

def get_tracer(name: str = "clinicaltrial-ai"):
    return trace.get_tracer(name)
