"""실행 통계 요약 객체의 외부 계약 테스트."""

import unittest

from toss_tech_blog_extractor.metrics import CrawlSummary


class CrawlSummaryTest(unittest.TestCase):
    def test_records_request_outcomes_and_retry_breakdown(self):
        summary = CrawlSummary()

        summary.record_request(success=True, retry_statuses=["429", "5xx"])
        summary.record_request(success=True, retry_statuses=[])
        summary.record_request(
            success=False, retry_statuses=["timeout", "client_error"]
        )
        summary.record_request(success=False, retry_statuses=["429"])

        self.assertEqual(summary.total_requests, 4)
        self.assertEqual(summary.success_count, 2)
        self.assertEqual(summary.failure_count, 2)
        self.assertEqual(summary.retry_count, 5)
        self.assertEqual(
            summary.retry_by_status,
            {"429": 2, "5xx": 1, "timeout": 1, "client_error": 1},
        )

    def test_retry_statuses_accept_canonical_http_and_timeout_names(self):
        summary = CrawlSummary()

        summary.record_request(
            success=True, retry_statuses=[429, 500, "TimeoutError", 400]
        )

        self.assertEqual(summary.retry_count, 4)
        self.assertEqual(
            summary.retry_by_status,
            {"429": 1, "5xx": 1, "timeout": 1, "client_error": 1},
        )

    def test_success_rate_is_zero_for_empty_run_and_percentage_for_run(self):
        self.assertEqual(CrawlSummary().success_rate, 0.0)

        summary = CrawlSummary()
        summary.record_request(success=True)
        summary.record_request(success=False)
        summary.record_request(success=True)

        self.assertAlmostEqual(summary.success_rate, 2 / 3)

    def test_elapsed_time_is_serialized_as_seconds(self):
        summary = CrawlSummary(started_at=100.0)
        summary.finish(finished_at=102.3456)

        self.assertAlmostEqual(summary.elapsed_seconds, 2.3456)
        payload = summary.to_dict()
        self.assertEqual(payload["total_requests"], 0)
        self.assertEqual(payload["success_count"], 0)
        self.assertEqual(payload["failure_count"], 0)
        self.assertEqual(payload["retry_count"], 0)
        self.assertEqual(payload["retry_by_status"], {})
        self.assertEqual(payload["success_rate"], 0.0)
        self.assertEqual(payload["elapsed_seconds"], 2.3456)


if __name__ == "__main__":
    unittest.main()
