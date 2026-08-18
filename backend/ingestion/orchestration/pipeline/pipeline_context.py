import uuid
from datetime import datetime
from .pipeline_state import PipelineState

class PipelineContext:
    """
    Context carrier passing intermediate data, metrics, execution IDs,
    and warnings/errors collections between pipeline stage executions.
    """
    def __init__(self, uploaded_document=None, user_info=None, max_retry=3):
        self.pipeline_id = f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4()}"
        self.uploaded_document = uploaded_document
        self.user_info = user_info
        
        # Stage Intermediate Outputs
        self.parser_result = None
        self.ocr_result = None
        self.metadata = None
        self.canonical_record = None
        self.standardized_record = None
        
        # Pipeline execution properties
        self.state = PipelineState.UPLOADED
        self.timestamps = {
            "start_time": datetime.now(),
            "end_time": None,
            "stages": {}  # stage_name -> {"start": dt, "end": dt, "duration": float}
        }
        self.warnings = []
        self.errors = []
        
        # Retry logic placeholders
        self.retry_count = 0
        self.max_retry = max_retry
        self.last_failed_stage = None

    def update_state(self, new_state: PipelineState):
        """Updates pipeline status state."""
        self.state = new_state
