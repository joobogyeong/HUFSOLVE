from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch


TEST_DIR = tempfile.TemporaryDirectory()
TEST_DB_PATH = Path(TEST_DIR.name) / "hufsolve-test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["QUEUE_BACKEND"] = "local"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["AUTO_SEED"] = "true"
os.environ["ARTIFACT_BACKEND"] = "local"
os.environ["ARTIFACT_LOCAL_DIR"] = str(Path(TEST_DIR.name) / "artifacts")
os.environ["LLM_REVIEW_ENABLED"] = "false"

from fastapi.testclient import TestClient

from backend.app.database import Base, SessionLocal, engine, init_db
from backend.app.main import app
from backend.app.artifacts import S3ArtifactStore, get_json, get_text
from backend.app.llm_review import _load_attempt_submissions, build_review_prompt
from backend.app.models import (
    Course,
    CourseEnrollment,
    CourseProfessor,
    ExamAttempt,
    ExamCourse,
    LlmReport,
    Problem,
    ProblemArtifact,
    Professor,
    SampleRun,
    Student,
    Submission,
    User,
)
from backend.app.queue.sqs import SqsQueueClient
from backend.app.seed import seed_database, synchronize_execution_artifacts
from backend.app.verify_storage import build_storage_report
from scripts.load_test import TERMINAL_STATUSES as LOAD_TEST_TERMINAL_STATUSES
from scripts.load_test import format_error as format_load_test_error
from scripts.load_test import submit_and_wait
from worker.judge import judge_sample_run, judge_submission
from worker.queue import LocalWorkerQueue, SqsWorkerQueue
from worker.review import generate_llm_report
from worker.docker_runner import _communicate_limited, run_python_code, settings as docker_runner_settings


class HufsolveIntegrationTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        TEST_DIR.cleanup()

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        init_db()
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()

    def test_api_lists_seeded_exams_and_creates_pending_submission(self) -> None:
        with TestClient(app) as client:
            exams_response = client.get("/exams")
            self.assertEqual(exams_response.status_code, 200)
            exams = exams_response.json()
            self.assertEqual(exams[0]["roomCode"], "HUF-2026")

            problem_id = exams[0]["problems"][0]["id"]
            submission_response = client.post(
                "/submissions",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": "a, b = map(int, input().split())\nprint(a+b)",
                },
            )
            self.assertEqual(submission_response.status_code, 202)
            submission_id = submission_response.json()["submissionId"]

            status_response = client.get(f"/submissions/{submission_id}")
            self.assertEqual(status_response.status_code, 200)
            self.assertEqual(status_response.json()["status"], "PENDING")

    def test_seed_creates_normalized_reference_tables_and_problem_artifacts(self) -> None:
        db = SessionLocal()
        try:
            self.assertEqual(db.query(User).filter(User.role == "PROFESSOR").count(), 2)
            self.assertEqual(db.query(Professor).count(), 2)
            self.assertEqual(db.query(Student).count(), 0)
            self.assertEqual(db.query(Course).count(), 2)
            self.assertEqual(db.query(CourseProfessor).count(), 2)
            self.assertEqual(db.query(ExamCourse).count(), 2)
            self.assertEqual(db.query(ProblemArtifact).count(), db.query(Problem).count())

            artifact = db.query(ProblemArtifact).order_by(ProblemArtifact.problem_id).first()
            statement = get_json(artifact.statement_s3_key)
            testcases = get_json(artifact.testcases_s3_key)
            self.assertIn("starter_code", statement)
            self.assertIn("reference_solution", statement)
            self.assertIn("print", statement["reference_solution"])
            self.assertGreater(len(testcases), 0)
            self.assertIn("expected_output", testcases[0])
        finally:
            db.close()

        report = build_storage_report()
        self.assertTrue(report["ok"])
        self.assertEqual(report["exams_without_course"], 0)
        self.assertEqual(report["problems_without_active_artifact"], 0)
        self.assertEqual(report["missing_object_keys"], [])

    def test_submission_source_and_result_are_stored_as_artifacts(self) -> None:
        source_code = "a, b = map(int, input().split())\nprint(a+b)"
        with TestClient(app) as client:
            problem_id = client.get("/exams").json()[0]["problems"][0]["id"]
            response = client.post(
                "/submissions",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": source_code,
                },
            )
            submission_id = response.json()["submissionId"]

        db = SessionLocal()
        try:
            submission = db.get(Submission, submission_id)
            self.assertNotEqual(submission.source_code, source_code)
            self.assertEqual(get_text(submission.artifact.source_s3_key), source_code)
        finally:
            db.close()

        def fake_run_python_code(
            source_code: str,
            input_data: str,
            time_limit_ms: int | None = None,
            memory_limit_mb: int | None = None,
        ) -> dict[str, object]:
            a, b = [int(part) for part in input_data.split()]
            return {
                "status": "OK",
                "stdout": str(a + b),
                "stderr": "",
                "execution_time_ms": 7,
            }

        with patch("worker.judge.run_python_code", side_effect=fake_run_python_code):
            judge_submission(submission_id)

        db = SessionLocal()
        try:
            submission = db.get(Submission, submission_id)
            result = get_json(submission.artifact.result_s3_key)
            self.assertEqual(result["submission_id"], submission_id)
            self.assertEqual(result["status"], "ACCEPTED")
        finally:
            db.close()

    def test_existing_submission_source_is_migrated_to_artifact_storage(self) -> None:
        source_code = "print('legacy')"
        db = SessionLocal()
        try:
            problem = db.query(Problem).order_by(Problem.id.asc()).first()
            submission = Submission(
                exam_id=problem.exam_id,
                problem_id=problem.id,
                language="python",
                source_code=source_code,
                status="ACCEPTED",
                score=100,
            )
            db.add(submission)
            db.commit()

            synchronize_execution_artifacts(db)
            db.commit()
            db.refresh(submission)

            self.assertNotEqual(submission.source_code, source_code)
            self.assertEqual(get_text(submission.artifact.source_s3_key), source_code)
            result = get_json(submission.artifact.result_s3_key)
            self.assertTrue(result["migrated_summary"])
        finally:
            db.close()

    def test_local_queue_claims_each_pending_submission_once(self) -> None:
        first_id = self._create_pending_submission()
        second_id = self._create_pending_submission()

        queue = LocalWorkerQueue()
        first_message = queue.receive()
        second_message = queue.receive()
        third_message = queue.receive()

        self.assertIsNotNone(first_message)
        self.assertIsNotNone(second_message)
        self.assertNotEqual(first_message.resource_id, second_message.resource_id)
        self.assertEqual({first_id, second_id}, {first_message.resource_id, second_message.resource_id})
        self.assertIsNone(third_message)

    def test_worker_marks_submission_accepted(self) -> None:
        submission_id = self._create_pending_submission()
        message = LocalWorkerQueue().receive()
        self.assertEqual(message.resource_id, submission_id)

        def fake_run_python_code(
            source_code: str,
            input_data: str,
            time_limit_ms: int | None = None,
            memory_limit_mb: int | None = None,
        ) -> dict[str, object]:
            a, b = [int(part) for part in input_data.split()]
            return {
                "status": "OK",
                "stdout": str(a + b),
                "stderr": "",
                "execution_time_ms": 12,
            }

        with patch("worker.judge.run_python_code", side_effect=fake_run_python_code):
            judge_submission(submission_id)

        submission = self._get_submission(submission_id)
        self.assertEqual(submission.status, "ACCEPTED")
        self.assertEqual(submission.passed_count, submission.total_count)
        self.assertEqual(submission.score, 100)

    def test_worker_marks_submission_time_limit_exceeded(self) -> None:
        submission_id = self._create_pending_submission()
        LocalWorkerQueue().receive()

        with patch(
            "worker.judge.run_python_code",
            return_value={
                "status": "TIME_LIMIT_EXCEEDED",
                "stdout": "",
                "stderr": "Time limit exceeded",
                "execution_time_ms": 2100,
            },
        ):
            judge_submission(submission_id)

        submission = self._get_submission(submission_id)
        self.assertEqual(submission.status, "TIME_LIMIT_EXCEEDED")
        self.assertEqual(submission.error_message, "Time limit exceeded")

    def test_local_queue_failure_marks_system_error(self) -> None:
        submission_id = self._create_pending_submission()
        queue = LocalWorkerQueue()
        message = queue.receive()

        queue.fail(message, RuntimeError("docker unavailable"))

        submission = self._get_submission(submission_id)
        self.assertEqual(submission.status, "SYSTEM_ERROR")
        self.assertEqual(submission.error_message, "docker unavailable")

    def test_sqs_queue_uses_receive_count_before_marking_system_error(self) -> None:
        queue = SqsWorkerQueue.__new__(SqsWorkerQueue)
        queue._client = FakeSqsClient(receive_count=3)

        message = queue.receive()
        self.assertEqual(message.task_type, "submission")
        self.assertEqual(message.resource_id, 42)
        self.assertEqual(message.receive_count, 3)

        with patch("worker.queue.mark_submission_system_error") as mark_system_error:
            queue.fail(message, RuntimeError("docker unavailable"))
            mark_system_error.assert_called_once_with(42, "docker unavailable")

    def test_sqs_queue_emits_minimal_sample_run_reference(self) -> None:
        queue = SqsQueueClient.__new__(SqsQueueClient)
        queue._client = FakeSqsSendClient()

        queue.enqueue_sample_run(201)

        payload = json.loads(queue._client.messages[0]["MessageBody"])
        self.assertEqual(
            payload,
            {
                "task_type": "sample_run",
                "sample_run_id": 201,
            },
        )

    def test_sqs_queue_emits_minimal_llm_report_reference(self) -> None:
        queue = SqsQueueClient.__new__(SqsQueueClient)
        queue._client = FakeSqsSendClient()

        queue.enqueue_llm_report(301)

        payload = json.loads(queue._client.messages[0]["MessageBody"])
        self.assertEqual(
            payload,
            {
                "task_type": "llm_report",
                "report_id": 301,
            },
        )

    def test_sqs_worker_parses_sample_run_reference(self) -> None:
        queue = SqsWorkerQueue.__new__(SqsWorkerQueue)
        queue._client = FakeSqsClient(
            receive_count=1,
            body={
                "task_type": "sample_run",
                "sample_run_id": 201,
            },
        )

        message = queue.receive()

        self.assertEqual(message.task_type, "sample_run")
        self.assertEqual(message.resource_id, 201)

    def test_sqs_worker_parses_llm_report_reference(self) -> None:
        queue = SqsWorkerQueue.__new__(SqsWorkerQueue)
        queue._client = FakeSqsClient(
            receive_count=1,
            body={
                "task_type": "llm_report",
                "report_id": 301,
            },
        )

        message = queue.receive()

        self.assertEqual(message.task_type, "llm_report")
        self.assertEqual(message.resource_id, 301)

    def test_s3_artifact_exists_uses_exact_key_listing(self) -> None:
        store = S3ArtifactStore.__new__(S3ArtifactStore)
        store._bucket_name = "artifact-bucket"
        store._client = FakeS3ListClient(
            keys=["problems/1/versions/1/statement.json.backup"]
        )
        self.assertFalse(store.exists("problems/1/versions/1/statement.json"))

        store._client = FakeS3ListClient(keys=["problems/1/versions/1/statement.json"])
        self.assertTrue(store.exists("problems/1/versions/1/statement.json"))

    def test_api_creates_sample_run_and_worker_completes_it(self) -> None:
        custom_input = "10 20"
        with TestClient(app) as client:
            problem_id = client.get("/exams").json()[0]["problems"][0]["id"]
            run_response = client.post(
                "/runs",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": "a, b = map(int, input().split())\nprint(a+b)",
                    "sampleIndex": 0,
                    "inputData": custom_input,
                },
            )
            self.assertEqual(run_response.status_code, 202)
            run_id = run_response.json()["runId"]

        message = LocalWorkerQueue().receive()
        self.assertEqual(message.task_type, "sample_run")
        self.assertEqual(message.resource_id, run_id)

        with patch(
            "worker.judge.run_python_code",
            return_value={
                "status": "OK",
                "stdout": "30\n",
                "stderr": "",
                "execution_time_ms": 9,
            },
        ) as run_code:
            judge_sample_run(run_id)
            self.assertEqual(run_code.call_args.kwargs["input_data"], custom_input)

        with TestClient(app) as client:
            payload = client.get(f"/runs/{run_id}").json()
            self.assertEqual(payload["status"], "COMPLETED")
            self.assertEqual(payload["input"], custom_input)
            self.assertEqual(payload["expectedOutput"], "3")
            self.assertEqual(payload["stdout"], "30\n")

    def test_api_preserves_empty_custom_run_input(self) -> None:
        with TestClient(app) as client:
            problem_id = client.get("/exams").json()[0]["problems"][0]["id"]
            response = client.post(
                "/runs",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": "print('no input required')",
                    "sampleIndex": 0,
                    "inputData": "",
                },
            )
            self.assertEqual(response.status_code, 202)
            run_id = response.json()["runId"]

        db = SessionLocal()
        try:
            sample_run = db.get(SampleRun, run_id)
            self.assertEqual(sample_run.input_data, "")
        finally:
            db.close()

    def test_api_rejects_out_of_range_sample_index(self) -> None:
        with TestClient(app) as client:
            problem_id = client.get("/exams").json()[0]["problems"][0]["id"]
            response = client.post(
                "/runs",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": "print('test')",
                    "sampleIndex": 99,
                },
            )
            self.assertEqual(response.status_code, 400)

    def test_api_rejects_oversized_source_code(self) -> None:
        with TestClient(app) as client:
            problem_id = client.get("/exams").json()[0]["problems"][0]["id"]
            response = client.post(
                "/submissions",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": "x" * 100_001,
                },
            )
            self.assertEqual(response.status_code, 422)

    def test_runner_capture_stops_after_output_limit(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-c", "print('x' * 10000)"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        with patch(
            "worker.docker_runner._terminate_execution",
            side_effect=lambda child, container_name: (child.kill(), child.wait())[1],
        ):
            stdout, stderr, timed_out, output_limit_exceeded = _communicate_limited(
                process=process,
                input_data=b"",
                timeout_sec=5,
                max_output_bytes=128,
                container_name="test-container",
            )

        self.assertFalse(timed_out)
        self.assertTrue(output_limit_exceeded)
        self.assertLessEqual(len(stdout) + len(stderr), 128)

    def test_runner_keeps_container_stdin_open(self) -> None:
        process = MagicMock(returncode=0)

        with (
            patch("worker.docker_runner.subprocess.Popen", return_value=process) as popen,
            patch(
                "worker.docker_runner._communicate_limited",
                return_value=(b"hello\n", b"", False, False),
            ),
            patch(
                "worker.docker_runner.settings",
                replace(docker_runner_settings, judge_base_tmp_dir=TEST_DIR.name),
            ),
        ):
            result = run_python_code("print(input())\n", "hello\n")

        command = popen.call_args.args[0]
        self.assertEqual(result["status"], "OK")
        self.assertIn("-i", command)
        self.assertLess(command.index("-i"), command.index("judge-python:3.11"))
        self.assertIn("--read-only", command)
        self.assertEqual(command[command.index("--cap-drop") + 1], "ALL")
        self.assertEqual(command[command.index("--security-opt") + 1], "no-new-privileges=true")
        self.assertEqual(command[command.index("--tmpfs") + 1], "/tmp:rw,noexec,nosuid,size=16m")
        self.assertIn("timeout", command)
        self.assertLess(command.index("timeout"), command.index("python3"))

    def test_runner_maps_container_timeout_to_time_limit_exceeded(self) -> None:
        process = MagicMock(returncode=124)

        with (
            patch("worker.docker_runner.subprocess.Popen", return_value=process),
            patch(
                "worker.docker_runner._communicate_limited",
                return_value=(b"", b"timeout: sending signal TERM to command 'python3'\n", False, False),
            ),
            patch(
                "worker.docker_runner.settings",
                replace(docker_runner_settings, judge_base_tmp_dir=TEST_DIR.name),
            ),
        ):
            result = run_python_code("while True:\n    pass\n", "")

        self.assertEqual(result["status"], "TIME_LIMIT_EXCEEDED")
        self.assertEqual(result["stderr"], "Time limit exceeded")

    def test_load_test_treats_output_limit_as_terminal(self) -> None:
        self.assertIn("OUTPUT_LIMIT_EXCEEDED", LOAD_TEST_TERMINAL_STATUSES)

    def test_exam_attempt_history_uses_backend_calculated_score(self) -> None:
        self._create_pending_submission(student_id="20260001", status="ACCEPTED")

        with TestClient(app) as client:
            created = client.post(
                "/exam-attempts",
                json={
                    "roomCode": "HUF-2026",
                    "studentId": "20260001",
                    "studentName": "테스트 학생",
                    "status": "최종 제출",
                },
            )
            self.assertEqual(created.status_code, 201)
            created_payload = created.json()
            self.assertEqual(created.json()["passedProblems"], 1)
            self.assertEqual(created.json()["totalProblems"], 3)
            self.assertEqual(created.json()["score"], 33)
            self.assertIsNotNone(created.json()["reportId"])

            history = client.get("/exam-attempts?studentId=20260001")
            self.assertEqual(history.status_code, 200)
            self.assertEqual(len(history.json()), 1)
            self.assertEqual(history.json()[0]["roomCode"], "HUF-2026")
            self.assertIsNotNone(history.json()[0]["reportId"])

            repeated = client.post(
                "/exam-attempts",
                json={
                    "roomCode": "HUF-2026",
                    "studentId": "20260001",
                    "studentName": "테스트 학생",
                    "status": "최종 제출",
                },
            )
            self.assertEqual(repeated.status_code, 201)
            self.assertEqual(repeated.json()["attemptId"], created_payload["attemptId"])
            self.assertEqual(repeated.json()["reportId"], created_payload["reportId"])
            self.assertEqual(repeated.json()["passedProblems"], 1)

        db = SessionLocal()
        try:
            self.assertEqual(
                db.query(Student).filter(Student.student_number == "20260001").count(),
                1,
            )
            self.assertEqual(db.query(CourseEnrollment).count(), 1)
        finally:
            db.close()

    def test_exam_attempt_without_submissions_does_not_enqueue_llm_report(self) -> None:
        with TestClient(app) as client:
            created = client.post(
                "/exam-attempts",
                json={
                    "roomCode": "HUF-2026",
                    "studentId": "20260000",
                    "studentName": "미제출 학생",
                    "status": "최종 제출",
                },
            )
            self.assertEqual(created.status_code, 201)
            self.assertIsNone(created.json()["reportId"])

        self.assertIsNone(LocalWorkerQueue().receive())

    def test_exam_attempt_creates_pending_llm_report(self) -> None:
        self._create_pending_submission(student_id="20260002", status="ACCEPTED")

        with TestClient(app) as client:
            created = client.post(
                "/exam-attempts",
                json={
                    "roomCode": "HUF-2026",
                    "studentId": "20260002",
                    "studentName": "리포트 학생",
                    "status": "최종 제출",
                },
            )
            self.assertEqual(created.status_code, 201)
            report_id = created.json()["reportId"]
            self.assertIsNotNone(report_id)
            report_response = client.get(f"/reports/{report_id}")
            self.assertEqual(report_response.status_code, 200)
            self.assertEqual(report_response.json()["status"], "PENDING")
            self.assertEqual(report_response.json()["language"], "ko")

        message = LocalWorkerQueue().receive()
        self.assertEqual(message.task_type, "llm_report")
        self.assertEqual(message.resource_id, report_id)

    def test_worker_generates_korean_fallback_llm_report(self) -> None:
        self._create_pending_submission(student_id="20260003", status="ACCEPTED")
        with TestClient(app) as client:
            created = client.post(
                "/exam-attempts",
                json={
                    "roomCode": "HUF-2026",
                    "studentId": "20260003",
                    "studentName": "리포트 학생",
                    "status": "최종 제출",
                },
            )
            report_id = created.json()["reportId"]

        LocalWorkerQueue().receive()
        generate_llm_report(report_id)

        db = SessionLocal()
        try:
            report = db.get(LlmReport, report_id)
            self.assertEqual(report.status, "COMPLETED")
            self.assertEqual(report.language, "ko")
            self.assertIn("리포트", report.summary)
            self.assertGreater(len(report.problem_reviews), 0)
        finally:
            db.close()

    def test_llm_prompt_includes_problem_reference_solution_and_submitted_code(self) -> None:
        submission_id = self._create_pending_submission(
            student_id="20260004",
            status="ACCEPTED",
        )

        with TestClient(app) as client:
            client.post(
                "/exam-attempts",
                json={
                    "roomCode": "HUF-2026",
                    "studentId": "20260004",
                    "studentName": "프롬프트 학생",
                    "status": "최종 제출",
                },
            )

        db = SessionLocal()
        try:
            submission = db.get(Submission, submission_id)
            attempt = (
                db.query(ExamAttempt)
                .filter(ExamAttempt.student_id == "20260004")
                .order_by(ExamAttempt.id.desc())
                .first()
            )
            prompt = build_review_prompt(attempt, [submission])
            payload = json.loads(prompt)
            item = payload["submissions"][0]
            self.assertIn("problem", item)
            self.assertIn("referenceSolutionCode", item)
            self.assertIn("submittedCode", item)
            self.assertIn("print", item["referenceSolutionCode"])
            self.assertIn("input", item["submittedCode"])
        finally:
            db.close()

    def test_llm_report_uses_latest_submission_per_student_problem(self) -> None:
        first_id = self._create_pending_submission(
            student_id="20260005",
            status="WRONG_ANSWER",
            source_code="print('old')",
        )
        second_id = self._create_pending_submission(
            student_id="20260005",
            status="ACCEPTED",
            source_code="a, b = map(int, input().split())\nprint(a+b)",
        )

        with TestClient(app) as client:
            client.post(
                "/exam-attempts",
                json={
                    "roomCode": "HUF-2026",
                    "studentId": "20260005",
                    "studentName": "최신제출 학생",
                    "status": "최종 제출",
                },
            )

        db = SessionLocal()
        try:
            attempt = (
                db.query(ExamAttempt)
                .filter(ExamAttempt.student_id == "20260005")
                .order_by(ExamAttempt.id.desc())
                .first()
            )
            submissions = _load_attempt_submissions(db, attempt)
            self.assertEqual([submission.id for submission in submissions], [second_id])
            self.assertNotIn(first_id, [submission.id for submission in submissions])

            prompt = build_review_prompt(attempt, submissions)
            item = json.loads(prompt)["submissions"][0]
            self.assertEqual(item["studentProblemKey"], "20260005_1")
        finally:
            db.close()

    def _create_pending_submission(
        self,
        student_id: str | None = None,
        status: str = "PENDING",
        source_code: str = "a, b = map(int, input().split())\nprint(a+b)",
    ) -> int:
        db = SessionLocal()
        try:
            problem = db.query(Problem).order_by(Problem.id.asc()).first()
            submission = Submission(
                exam_id=problem.exam_id,
                problem_id=problem.id,
                student_id=student_id,
                language="python",
                source_code=source_code,
                status=status,
                total_count=len(problem.testcases),
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)
            return submission.id
        finally:
            db.close()

    def _get_submission(self, submission_id: int) -> Submission:
        db = SessionLocal()
        try:
            submission = db.get(Submission, submission_id)
            db.expunge(submission)
            return submission
        finally:
            db.close()


class FakeSqsClient:
    def __init__(self, receive_count: int, body: dict[str, object] | None = None) -> None:
        self.receive_count = receive_count
        self.body = body or {"submission_id": 42}

    def receive_message(self, **kwargs: object) -> dict[str, object]:
        return {
            "Messages": [
                {
                    "ReceiptHandle": "receipt-handle",
                    "Body": json.dumps(self.body),
                    "Attributes": {
                        "ApproximateReceiveCount": str(self.receive_count),
                    },
                }
            ]
        }


class FakeSqsSendClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    def send_message(self, **kwargs: object) -> None:
        self.messages.append(kwargs)


class FakeS3ListClient:
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        prefix = str(kwargs["Prefix"])
        return {
            "Contents": [{"Key": key} for key in self.keys if key.startswith(prefix)],
        }


class FakeLoadTestResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class RetryPollingClient:
    def __init__(self) -> None:
        self.poll_count = 0

    async def post(self, *_args: object, **_kwargs: object) -> FakeLoadTestResponse:
        return FakeLoadTestResponse({"submissionId": 1, "status": "PENDING"})

    async def get(self, *_args: object, **_kwargs: object) -> FakeLoadTestResponse:
        self.poll_count += 1
        if self.poll_count == 1:
            raise TimeoutError()
        return FakeLoadTestResponse({"status": "ACCEPTED"})


class LoadTestScriptTest(unittest.IsolatedAsyncioTestCase):
    async def test_polling_retries_transient_request_error(self) -> None:
        client = RetryPollingClient()

        metric = await submit_and_wait(
            client=client,
            problem_id=1,
            source_code="print(3)",
            poll_interval=0,
            poll_timeout=1,
            student_prefix="test",
            sequence=1,
        )

        self.assertTrue(metric.ok)
        self.assertEqual(metric.final_status, "ACCEPTED")
        self.assertEqual(client.poll_count, 2)

    async def test_error_formatter_preserves_exception_type(self) -> None:
        self.assertEqual(format_load_test_error(TimeoutError()), "TimeoutError: TimeoutError()")


if __name__ == "__main__":
    unittest.main()
