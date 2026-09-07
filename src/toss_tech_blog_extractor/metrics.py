"""크롤링 실행 결과를 집계하는 모델."""

import time
from collections.abc import Iterable
from dataclasses import dataclass, field


def _normalize_retry_status(status: object) -> str:
    """재시도 원인을 사용자에게 보여 줄 범주로 정규화한다."""
    if isinstance(status, int):
        if status == 429:
            return "429"
        if 500 <= status < 600:
            return "5xx"
        return "client_error"

    normalized = str(status).strip().lower()
    if normalized == "429":
        return "429"
    if normalized == "5xx" or normalized.startswith("5"):
        return "5xx"
    if normalized in {"timeout", "timeouterror"}:
        return "timeout"
    return "client_error"


@dataclass
class CrawlSummary:
    """한 번의 본문 수집 실행에서 발생한 결과와 재시도를 집계한다."""

    started_at: float = field(default_factory=time.perf_counter)
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    retry_by_status: dict[str, int] = field(default_factory=dict)
    _finished_at: float | None = field(default=None, init=False, repr=False)

    def record_request(
        self,
        *,
        success: bool,
        retry_statuses: Iterable[object] | None = None,
    ) -> None:
        """URL 하나의 최종 결과와 실제 재시도 원인을 기록한다."""
        self.total_requests += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        for status in retry_statuses or ():
            normalized = _normalize_retry_status(status)
            self.retry_count += 1
            self.retry_by_status[normalized] = (
                self.retry_by_status.get(normalized, 0) + 1
            )

    @property
    def success_rate(self) -> float:
        """전체 요청 중 최종 성공 비율을 0~1 범위로 반환한다."""
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests

    @property
    def elapsed_seconds(self) -> float:
        """실행 시작부터 종료까지의 단조 시계 경과 시간을 반환한다."""
        finished_at = self._finished_at
        if finished_at is None:
            finished_at = time.perf_counter()
        return finished_at - self.started_at

    def finish(self, *, finished_at: float | None = None) -> None:
        """요약의 종료 시각을 확정한다."""
        self._finished_at = time.perf_counter() if finished_at is None else finished_at

    def to_dict(self) -> dict[str, object]:
        """로그·JSON 출력에 사용할 직렬화 가능한 사전을 반환한다."""
        return {
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "retry_count": self.retry_count,
            "retry_by_status": dict(self.retry_by_status),
            "success_rate": self.success_rate,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
        }

    def format_text(self) -> str:
        """CLI에 표시할 한 줄 실행 요약을 만든다."""
        retry_details = ", ".join(
            f"{status} {count}회" for status, count in self.retry_by_status.items()
        )
        retry_text = f" (사유: {retry_details})" if retry_details else ""
        return (
            f"실행 요약 | 전체 {self.total_requests}개 | "
            f"성공 {self.success_count}개 | 실패 {self.failure_count}개 | "
            f"성공률 {self.success_rate:.1%} | 재시도 {self.retry_count}회"
            f"{retry_text} | 소요 {self.elapsed_seconds:.2f}초"
        )
