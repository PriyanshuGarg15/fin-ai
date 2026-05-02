import logging
import json
from contextvars import ContextVar

correlation_id_var: ContextVar[str]= ContextVar("correlation_id", default='none')

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id_var.get()
        return True
    
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data={
            "correlation_id": record.correlation_id,
            "message": record.getMessage(),
            "level": record.levelname,
            "timestamp": self.formatTime(record),
            "service": "fintech-ai-platform"
        }
        if(record.exc_info):
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)
    
def setup_logger():
    handler=logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    handler.addFilter(CorrelationIdFilter())
    logging.basicConfig(handlers=[handler], level=logging.INFO)
    return logging.getLogger(__name__) 