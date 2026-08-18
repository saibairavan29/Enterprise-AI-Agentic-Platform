import time
import logging
from datetime import datetime
from .pipeline_context import PipelineContext
from .pipeline_state import PipelineState
from .pipeline_result import PipelineResult
from ..exceptions.orchestration_exceptions import StageExecutionException

logger = logging.getLogger('enterprise')

class Pipeline:
    """
    Ingestion Stage Orchestrator. Coordinates dynamic pipelines execution flow
    sequentially, logging tracing hooks and computing performance statistics.
    """
    def __init__(self):
        self.stages = []

    def register_stage(self, stage):
        """Registers a pipeline processing stage."""
        self.stages.append(stage)
        return self

    # Logger Correlation Mappers
    def _log_msg(self, context: PipelineContext, stage_name, msg, level="info"):
        doc_id = context.uploaded_document.id if context.uploaded_document else "None"
        user_id = context.user_info.username if context.user_info else "Anonymous"
        corr_prefix = f"[Pipeline: {context.pipeline_id} | Doc: {doc_id} | User: {user_id} | Stage: {stage_name}]"
        
        if level == "error":
            logger.error(f"{corr_prefix} {msg}")
        elif level == "warning":
            logger.warning(f"{corr_prefix} {msg}")
        else:
            logger.info(f"{corr_prefix} {msg}")

    # Lifecycle Hooks
    def before_pipeline_start(self, context: PipelineContext):
        self._log_msg(context, "Start", "Pipeline execution start triggered.")

    def before_stage_execution(self, stage, context: PipelineContext):
        self._log_msg(context, stage.name, "Stage processing started.")

    def after_stage_execution(self, stage, result, context: PipelineContext):
        self._log_msg(context, stage.name, f"Stage finished with status: {result.get('status')}")

    def on_stage_failure(self, stage, error, context: PipelineContext):
        self._log_msg(context, stage.name, f"Stage execution failed: {str(error)}", level="error")
        context.errors.append(f"Stage '{stage.name}' failed: {str(error)}")
        context.last_failed_stage = stage.name

    def before_pipeline_complete(self, context: PipelineContext):
        self._log_msg(context, "Completion", "Beginning pipeline teardown tasks.")

    def after_pipeline_complete(self, context: PipelineContext):
        self._log_msg(context, "Teardown", f"Pipeline completed. Final state status: {context.state.value}")

    def run(self, context: PipelineContext) -> PipelineResult:
        """
        Executes all registered stages sequentially under custom hooks.
        """
        self.before_pipeline_start(context)
        
        stages_execution_report = {}
        successful_stages = 0
        failed_stages = 0
        skipped_stages = 0
        
        start_time = time.perf_counter()

        for stage in self.stages:
            stage_start_time = time.perf_counter()
            self.before_stage_execution(stage, context)
            
            try:
                # Invoke Standard Stage Contract
                result = stage.execute(context)
                stage_elapsed = round(time.perf_counter() - stage_start_time, 4)
                
                status = result.get("status", "SUCCESS")
                
                context.timestamps["stages"][stage.name] = {
                    "start": datetime.now(),
                    "end": datetime.now(),
                    "duration": stage_elapsed,
                    "status": status
                }

                stages_execution_report[stage.name] = {
                    "status": status,
                    "execution_time": stage_elapsed
                }

                if status == "SUCCESS":
                    successful_stages += 1
                elif status == "SKIPPED":
                    skipped_stages += 1
                else:
                    failed_stages += 1
                    raise StageExecutionException(stage.name, f"Stage returned error state status: {status}")

                self.after_stage_execution(stage, result, context)

            except Exception as e:
                failed_stages += 1
                self.on_stage_failure(stage, e, context)
                context.update_state(PipelineState.FAILED)
                
                stage_elapsed = round(time.perf_counter() - stage_start_time, 4)
                context.timestamps["stages"][stage.name] = {
                    "start": datetime.now(),
                    "end": datetime.now(),
                    "duration": stage_elapsed,
                    "status": "FAILED"
                }
                stages_execution_report[stage.name] = {
                    "status": "FAILED",
                    "execution_time": stage_elapsed
                }
                # Halt execution immediately on stage failure
                break

        # Pipeline stats collation
        context.timestamps["end_time"] = datetime.now()
        total_duration = round(time.perf_counter() - start_time, 4)

        if context.state != PipelineState.FAILED:
            context.update_state(PipelineState.COMPLETED)

        self.before_pipeline_complete(context)

        # Centralized computations
        total_executed = successful_stages + failed_stages + skipped_stages
        stage_durations = [s["duration"] for s in context.timestamps["stages"].values()]
        avg_stage_dur = round(sum(stage_durations) / len(stage_durations), 4) if stage_durations else 0.0

        slowest_stage = None
        fastest_stage = None
        if context.timestamps["stages"]:
            slowest_stage = max(context.timestamps["stages"], key=lambda k: context.timestamps["stages"][k]["duration"])
            fastest_stage = min(context.timestamps["stages"], key=lambda k: context.timestamps["stages"][k]["duration"])

        # Record Centralized Metrics to context
        if context.metadata is None:
            context.metadata = {}
            
        context.metadata["pipeline_metrics"] = {
            "total_pipeline_duration": total_duration,
            "total_stages_executed": total_executed,
            "successful_stages": successful_stages,
            "failed_stages": failed_stages,
            "skipped_stages": skipped_stages,
            "retry_attempts": context.retry_count,
            "average_stage_duration": avg_stage_dur,
            "slowest_stage": slowest_stage,
            "fastest_stage": fastest_stage
        }

        self.after_pipeline_complete(context)
        
        doc_id = context.uploaded_document.id if context.uploaded_document else ""

        return PipelineResult(
            success=(context.state == PipelineState.COMPLETED),
            document_id=doc_id,
            pipeline_id=context.pipeline_id,
            processing_status=context.state.value,
            pipeline_duration=total_duration,
            stage_execution=stages_execution_report,
            metadata=context.metadata,
            standardized_record=context.standardized_record,
            warnings=context.warnings,
            errors=context.errors
        )
