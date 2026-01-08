#!/usr/bin/env python3
"""
Integration Test for Coach Vocabulary API

This script tests the complete business logic flow through API calls.
It uses a test database and manipulates time via direct DB updates to
simulate various scenarios.

Test Scenarios:
1. User Registration & Login
2. Learn Mode - Basic Flow
3. Practice Mode - Answer Correct (P Pool Progression)
4. Practice Mode - Answer Wrong (Move to R Pool)
5. Review Mode - Review Phase (Display)
6. Review Mode - Practice Phase (Answer Correct → Back to P)
7. Review Mode - Practice Phase (Answer Wrong → Stay in R)
8. Daily Learn Limit (50 words)
9. P1 Pool Limit (10 words)
10. Complete P Pool Progression (P1 → P6)
11. Exercise Type Verification

Usage:
    # Start test server first (in another terminal):
    DATABASE_URL=postgresql://ianchen@localhost:5432/coach_vocabulary_test \
        uvicorn app.main:app --port 8001

    # Run tests:
    python tests/integration_test.py
"""

import json
import requests
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_DB_URL = "postgresql://ianchen@localhost:5432/coach_vocabulary_test"


class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class TestCase:
    name: str
    result: TestResult
    message: str = ""


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class IntegrationTest:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.user_id: Optional[str] = None
        self.test_results: List[TestCase] = []
        self.db_connection = None

    def setup_db(self):
        """Connect to test database for direct manipulation."""
        import psycopg2
        self.db_connection = psycopg2.connect(TEST_DB_URL)
        self.db_connection.autocommit = True

    def teardown_db(self):
        """Close database connection."""
        if self.db_connection:
            self.db_connection.close()

    def execute_sql(self, sql: str, params: tuple = None):
        """Execute SQL directly on test database."""
        with self.db_connection.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.description:
                return cursor.fetchall()
            return None

    def reset_test_data(self):
        """Reset all test data in the database."""
        self.execute_sql("DELETE FROM word_progress")
        self.execute_sql("DELETE FROM users")
        print(f"{Colors.BLUE}Test data reset{Colors.RESET}")

    def set_word_time(self, word_id: str, time_offset_minutes: int):
        """Set next_available_time for a word (for testing time-based logic)."""
        new_time = datetime.now(timezone.utc) + timedelta(minutes=time_offset_minutes)
        self.execute_sql(
            "UPDATE word_progress SET next_available_time = %s WHERE word_id = %s AND user_id = %s",
            (new_time, word_id, self.user_id)
        )

    def set_review_phase(self, word_id: str, is_in_review: bool):
        """Set is_in_review_phase for a word."""
        self.execute_sql(
            "UPDATE word_progress SET is_in_review_phase = %s WHERE word_id = %s AND user_id = %s",
            (is_in_review, word_id, self.user_id)
        )

    def set_pool(self, word_id: str, pool: str):
        """Set pool for a word."""
        self.execute_sql(
            "UPDATE word_progress SET pool = %s WHERE word_id = %s AND user_id = %s",
            (pool, word_id, self.user_id)
        )

    def get_word_progress(self, word_id: str) -> Optional[Dict]:
        """Get word progress from database."""
        result = self.execute_sql(
            "SELECT pool, is_in_review_phase, next_available_time FROM word_progress WHERE word_id = %s AND user_id = %s",
            (word_id, self.user_id)
        )
        if result:
            return {
                "pool": result[0][0],
                "is_in_review_phase": result[0][1],
                "next_available_time": result[0][2]
            }
        return None

    def count_user_progress(self) -> int:
        """Count total word progress records for user."""
        result = self.execute_sql(
            "SELECT COUNT(*) FROM word_progress WHERE user_id = %s",
            (self.user_id,)
        )
        return result[0][0] if result else 0

    def get_word_ids_from_db(self, limit: int = 50) -> List[str]:
        """Get word IDs directly from database."""
        result = self.execute_sql(
            "SELECT id FROM words ORDER BY id LIMIT %s",
            (limit,)
        )
        return [str(row[0]) for row in result] if result else []

    # === API Helpers ===

    def api_get(self, endpoint: str) -> requests.Response:
        """Make GET request with user ID header."""
        headers = {"X-User-Id": self.user_id} if self.user_id else {}
        return requests.get(f"{self.base_url}{endpoint}", headers=headers)

    def api_post(self, endpoint: str, data: Dict = None) -> requests.Response:
        """Make POST request with user ID header."""
        headers = {"X-User-Id": self.user_id, "Content-Type": "application/json"} if self.user_id else {"Content-Type": "application/json"}
        return requests.post(f"{self.base_url}{endpoint}", headers=headers, json=data)

    def record_result(self, name: str, passed: bool, message: str = ""):
        """Record test result."""
        result = TestResult.PASS if passed else TestResult.FAIL
        self.test_results.append(TestCase(name, result, message))

        color = Colors.GREEN if passed else Colors.RED
        status = "PASS" if passed else "FAIL"
        print(f"  {color}[{status}]{Colors.RESET} {name}")
        if message and not passed:
            print(f"         {Colors.YELLOW}{message}{Colors.RESET}")

    # === Test Cases ===

    def test_01_login(self):
        """Test user login/registration."""
        print(f"\n{Colors.BOLD}Test 1: User Login{Colors.RESET}")

        # New user
        resp = requests.post(f"{self.base_url}/api/auth/login", json={"username": "test_user"})
        data = resp.json()

        self.record_result(
            "New user registration",
            resp.status_code == 200 and data.get("is_new_user") == True,
            f"Status: {resp.status_code}, Response: {data}"
        )

        self.user_id = data.get("id")

        # Existing user
        resp = requests.post(f"{self.base_url}/api/auth/login", json={"username": "test_user"})
        data = resp.json()

        self.record_result(
            "Existing user login",
            resp.status_code == 200 and data.get("is_new_user") == False,
            f"Status: {resp.status_code}"
        )

    def test_02_initial_stats(self):
        """Test initial home stats for new user."""
        print(f"\n{Colors.BOLD}Test 2: Initial Home Stats{Colors.RESET}")

        resp = self.api_get("/api/home/stats")
        data = resp.json()

        self.record_result(
            "Today learned is 0",
            data.get("today_learned") == 0,
            f"today_learned: {data.get('today_learned')}"
        )

        self.record_result(
            "Can learn is true",
            data.get("can_learn") == True,
            f"can_learn: {data.get('can_learn')}"
        )

        self.record_result(
            "Can practice is false (no words learned)",
            data.get("can_practice") == False,
            f"can_practice: {data.get('can_practice')}"
        )

    def test_03_learn_session(self):
        """Test learn session and completion."""
        print(f"\n{Colors.BOLD}Test 3: Learn Session{Colors.RESET}")

        # Get learn session
        resp = self.api_get("/api/learn/session")
        data = resp.json()

        self.record_result(
            "Learn session available",
            data.get("available") == True,
            f"available: {data.get('available')}, reason: {data.get('reason')}"
        )

        self.record_result(
            "Session has 5 words",
            len(data.get("words", [])) == 5,
            f"words count: {len(data.get('words', []))}"
        )

        self.record_result(
            "Session has 5 exercises",
            len(data.get("exercises", [])) == 5,
            f"exercises count: {len(data.get('exercises', []))}"
        )

        # Store word IDs for later tests
        self.learned_word_ids = [w["id"] for w in data.get("words", [])]

        # Complete learning
        resp = self.api_post("/api/learn/complete", {"word_ids": self.learned_word_ids})
        data = resp.json()

        self.record_result(
            "Learning completed successfully",
            data.get("success") == True and data.get("words_moved") == 5,
            f"success: {data.get('success')}, words_moved: {data.get('words_moved')}"
        )

        # Verify words are in P1
        progress = self.get_word_progress(self.learned_word_ids[0])
        self.record_result(
            "Words moved to P1",
            progress and progress["pool"] == "P1",
            f"pool: {progress['pool'] if progress else 'None'}"
        )

    def test_04_practice_not_available_yet(self):
        """Test that practice is not available immediately after learning."""
        print(f"\n{Colors.BOLD}Test 4: Practice Not Available Yet{Colors.RESET}")

        resp = self.api_get("/api/practice/session")
        data = resp.json()

        self.record_result(
            "Practice not available (time not passed)",
            data.get("available") == False,
            f"available: {data.get('available')}, reason: {data.get('reason')}"
        )

    def test_05_practice_after_time(self):
        """Test practice after time has passed."""
        print(f"\n{Colors.BOLD}Test 5: Practice After Time Passed{Colors.RESET}")

        # Set time to past (simulate 10 minutes passed)
        for word_id in self.learned_word_ids:
            self.set_word_time(word_id, -1)  # 1 minute in the past

        resp = self.api_get("/api/practice/session")
        data = resp.json()

        self.record_result(
            "Practice now available",
            data.get("available") == True,
            f"available: {data.get('available')}"
        )

        self.record_result(
            "Exercise type is reading_lv1 (P1)",
            all(e.get("type") == "reading_lv1" for e in data.get("exercises", [])),
            f"types: {[e.get('type') for e in data.get('exercises', [])]}"
        )

        # Store for next test
        self.practice_exercises = data.get("exercises", [])

    def test_06_practice_answer_correct(self):
        """Test practice with correct answers - words move to P2."""
        print(f"\n{Colors.BOLD}Test 6: Practice Answer Correct (P1 → P2){Colors.RESET}")

        # Answer all correct
        answers = [{"word_id": e["word_id"], "correct": True} for e in self.practice_exercises]

        resp = self.api_post("/api/practice/submit", {"answers": answers})
        data = resp.json()

        self.record_result(
            "Submit successful",
            data.get("success") == True,
            f"success: {data.get('success')}"
        )

        self.record_result(
            "All answers correct",
            data.get("summary", {}).get("correct_count") == 5,
            f"correct_count: {data.get('summary', {}).get('correct_count')}"
        )

        # Check first word moved to P2
        first_result = data.get("results", [{}])[0]
        self.record_result(
            "Words moved from P1 to P2",
            first_result.get("previous_pool") == "P1" and first_result.get("new_pool") == "P2",
            f"previous: {first_result.get('previous_pool')}, new: {first_result.get('new_pool')}"
        )

    def test_07_practice_answer_wrong(self):
        """Test practice with wrong answers - words move to R pool."""
        print(f"\n{Colors.BOLD}Test 7: Practice Answer Wrong (P2 → R2){Colors.RESET}")

        # Make words available for practice
        for word_id in self.learned_word_ids:
            self.set_word_time(word_id, -1)

        # Get practice session
        resp = self.api_get("/api/practice/session")
        data = resp.json()

        if not data.get("available"):
            self.record_result("Practice available", False, "Practice not available")
            return

        exercises = data.get("exercises", [])

        # Answer first 2 wrong, rest correct
        answers = []
        for i, e in enumerate(exercises):
            answers.append({"word_id": e["word_id"], "correct": i >= 2})

        resp = self.api_post("/api/practice/submit", {"answers": answers})
        data = resp.json()

        # Check wrong answers moved to R pool
        wrong_results = [r for r in data.get("results", []) if r.get("correct") == False]

        self.record_result(
            "Wrong answers move to R2",
            all(r.get("new_pool") == "R2" for r in wrong_results),
            f"new_pools: {[r.get('new_pool') for r in wrong_results]}"
        )

        # Store R pool word for review tests
        if wrong_results:
            self.r_pool_word_id = wrong_results[0].get("word_id")

            # Verify is_in_review_phase is True
            progress = self.get_word_progress(self.r_pool_word_id)
            self.record_result(
                "R pool word is in review phase",
                progress and progress.get("is_in_review_phase") == True,
                f"is_in_review_phase: {progress.get('is_in_review_phase') if progress else 'None'}"
            )

    def test_08_review_session(self):
        """Test review session for R pool words."""
        print(f"\n{Colors.BOLD}Test 8: Review Session{Colors.RESET}")

        # Make R pool words available
        if hasattr(self, 'r_pool_word_id'):
            self.set_word_time(self.r_pool_word_id, -1)

        resp = self.api_get("/api/review/session")
        data = resp.json()

        # May not have enough words for review (need 3)
        if data.get("available") == False and data.get("reason") == "not_enough_words":
            self.record_result(
                "Review needs minimum 3 words",
                True,
                "Not enough R pool words for review - this is expected"
            )

            # Create more R pool words by learning and failing
            self._create_more_r_pool_words()

            resp = self.api_get("/api/review/session")
            data = resp.json()

        self.record_result(
            "Review session available",
            data.get("available") == True,
            f"available: {data.get('available')}, reason: {data.get('reason')}"
        )

        if data.get("available"):
            self.review_word_ids = [w["id"] for w in data.get("words", [])]
            self.review_exercises = data.get("exercises", [])

    def _create_more_r_pool_words(self):
        """Helper to create more R pool words for testing."""
        # Learn more words
        resp = self.api_get("/api/learn/session")
        if resp.json().get("available"):
            word_ids = [w["id"] for w in resp.json().get("words", [])]
            self.api_post("/api/learn/complete", {"word_ids": word_ids})

            # Make available and fail them
            for word_id in word_ids:
                self.set_word_time(word_id, -1)

            resp = self.api_get("/api/practice/session")
            if resp.json().get("available"):
                exercises = resp.json().get("exercises", [])
                answers = [{"word_id": e["word_id"], "correct": False} for e in exercises]
                self.api_post("/api/practice/submit", {"answers": answers})

                # Make R pool words available for review
                for word_id in word_ids:
                    self.set_word_time(word_id, -1)

    def test_09_review_complete(self):
        """Test completing review display phase."""
        print(f"\n{Colors.BOLD}Test 9: Review Complete (Display Phase){Colors.RESET}")

        if not hasattr(self, 'review_word_ids') or not self.review_word_ids:
            self.record_result("Review complete", False, "No review words available")
            return

        resp = self.api_post("/api/review/complete", {"word_ids": self.review_word_ids})
        data = resp.json()

        self.record_result(
            "Review complete successful",
            data.get("success") == True,
            f"success: {data.get('success')}"
        )

        # Verify is_in_review_phase is now False
        progress = self.get_word_progress(self.review_word_ids[0])
        self.record_result(
            "Word exits review phase (enters practice phase)",
            progress and progress.get("is_in_review_phase") == False,
            f"is_in_review_phase: {progress.get('is_in_review_phase') if progress else 'None'}"
        )

    def test_10_r_pool_practice_correct(self):
        """Test R pool practice phase - answer correct returns to P pool."""
        print(f"\n{Colors.BOLD}Test 10: R Pool Practice Correct (R → P){Colors.RESET}")

        if not hasattr(self, 'review_word_ids') or not self.review_word_ids:
            self.record_result("R pool practice", False, "No review words available")
            return

        # Make words available for practice (simulate 20 hours passed)
        for word_id in self.review_word_ids:
            self.set_word_time(word_id, -1)

        # Get practice session (R pool words in practice phase will appear here)
        resp = self.api_get("/api/practice/session")
        data = resp.json()

        if not data.get("available"):
            self.record_result("R pool practice available", False, f"Practice not available: {data.get('reason')}")
            return

        exercises = data.get("exercises", [])

        # Find R pool exercises
        r_exercises = [e for e in exercises if e.get("pool", "").startswith("R")]

        if not r_exercises:
            self.record_result("R pool exercises found", False, "No R pool exercises in session")
            return

        # Get the R pool number to verify correct return
        r_pool = r_exercises[0].get("pool")  # e.g., "R2"
        expected_p_pool = "P" + r_pool[1]  # e.g., "P2"

        # Answer R pool word correct
        answers = [{"word_id": r_exercises[0]["word_id"], "correct": True}]

        # Add other exercises as correct too
        for e in exercises:
            if e["word_id"] != r_exercises[0]["word_id"]:
                answers.append({"word_id": e["word_id"], "correct": True})

        resp = self.api_post("/api/practice/submit", {"answers": answers})
        data = resp.json()

        # Find R pool result
        r_result = next((r for r in data.get("results", []) if r.get("word_id") == r_exercises[0]["word_id"]), None)

        if r_result:
            self.record_result(
                f"R pool word returns to correct P pool ({r_pool} → {expected_p_pool})",
                r_result.get("new_pool") == expected_p_pool,
                f"previous: {r_result.get('previous_pool')}, new: {r_result.get('new_pool')}, expected: {expected_p_pool}"
            )
        else:
            self.record_result("R pool result found", False, "No result for R pool word")

    def test_11_r_pool_practice_wrong(self):
        """Test R pool practice phase - answer wrong stays in R pool."""
        print(f"\n{Colors.BOLD}Test 11: R Pool Practice Wrong (Stay in R){Colors.RESET}")

        # Reset and create fresh user for isolation
        self.reset_test_data()
        resp = requests.post(f"{self.base_url}/api/auth/login", json={"username": "r_pool_wrong_test"})
        self.user_id = resp.json().get("id")

        # Learn 5 words
        resp = self.api_get("/api/learn/session")
        if not resp.json().get("available"):
            self.record_result("Learn for R pool test", False, "Cannot learn new words")
            return

        words = resp.json().get("words", [])
        word_ids = [w["id"] for w in words]
        target_word_id = word_ids[0]
        self.api_post("/api/learn/complete", {"word_ids": word_ids})

        # Make all words available for practice
        for wid in word_ids:
            self.set_word_time(wid, -1)

        # Get practice and make target word wrong (moves to R1)
        resp = self.api_get("/api/practice/session")
        if not resp.json().get("available"):
            self.record_result("Practice available", False, "Practice not available")
            return

        exercises = resp.json().get("exercises", [])
        answers = []
        for e in exercises:
            # Answer wrong for target word only
            answers.append({"word_id": e["word_id"], "correct": e["word_id"] != target_word_id})

        resp = self.api_post("/api/practice/submit", {"answers": answers})

        # Verify target word moved to R1 (since it was in P1)
        progress = self.get_word_progress(target_word_id)
        if not progress or progress["pool"] != "R1":
            self.record_result("Word moved to R1", False, f"pool: {progress['pool'] if progress else 'None'}")
            return

        self.record_result(
            "Word moved to R1 with review phase",
            progress["is_in_review_phase"] == True,
            f"is_in_review_phase: {progress['is_in_review_phase']}"
        )

        # Complete review phase for target word (simulate review complete)
        self.set_review_phase(target_word_id, False)
        self.set_word_time(target_word_id, -1)

        # Make other 4 words available for practice (need 5 total)
        for wid in word_ids[1:]:
            self.set_word_time(wid, -1)

        # Get practice session - R1 word in practice phase should be included
        resp = self.api_get("/api/practice/session")
        if not resp.json().get("available"):
            self.record_result("R pool practice available", False, "Practice not available")
            return

        exercises = resp.json().get("exercises", [])
        r_exercise = next((e for e in exercises if e.get("word_id") == target_word_id), None)

        if not r_exercise:
            self.record_result("R pool word in practice", False, "R pool word not in practice session")
            return

        # Answer wrong again
        answers = []
        for e in exercises:
            answers.append({"word_id": e["word_id"], "correct": e["word_id"] != target_word_id})

        resp = self.api_post("/api/practice/submit", {"answers": answers})
        data = resp.json()

        # Find result for our word
        result = next((r for r in data.get("results", []) if r.get("word_id") == target_word_id), None)

        if result:
            self.record_result(
                "R pool word stays in R pool on wrong answer",
                result.get("previous_pool") == "R1" and result.get("new_pool") == "R1",
                f"previous: {result.get('previous_pool')}, new: {result.get('new_pool')}"
            )

            # Verify re-entered review phase
            progress = self.get_word_progress(target_word_id)
            self.record_result(
                "R pool word re-enters review phase",
                progress and progress.get("is_in_review_phase") == True,
                f"is_in_review_phase: {progress.get('is_in_review_phase') if progress else 'None'}"
            )
        else:
            self.record_result("R pool result found", False, "No result for R pool word")

    def test_12_p_pool_full_progression(self):
        """Test complete P pool progression P1 → P2 → P3 → P4 → P5 → P6 with exercise type verification."""
        print(f"\n{Colors.BOLD}Test 12: Complete P Pool Progression{Colors.RESET}")

        # Reset and create fresh user for isolation
        self.reset_test_data()
        resp = requests.post(f"{self.base_url}/api/auth/login", json={"username": "progression_test"})
        self.user_id = resp.json().get("id")

        # Learn 5 words (minimum for practice)
        resp = self.api_get("/api/learn/session")
        if not resp.json().get("available"):
            self.record_result("Learn for progression", False, "Cannot learn new words")
            return

        words = resp.json().get("words", [])
        all_word_ids = [w["id"] for w in words]
        word_id = all_word_ids[0]  # Track first word through progression
        self.api_post("/api/learn/complete", {"word_ids": all_word_ids})

        expected_progression = [
            ("P1", "P2", "reading_lv1"),
            ("P2", "P3", "listening_lv1"),
            ("P3", "P4", "speaking_lv1"),
            ("P4", "P5", "reading_lv2"),
            ("P5", "P6", "speaking_lv2"),
        ]

        for from_pool, to_pool, expected_type in expected_progression:
            # Make ALL words available for practice (need 5 minimum)
            for wid in all_word_ids:
                self.set_word_time(wid, -1)

            # Get current pool
            progress = self.get_word_progress(word_id)
            current_pool = progress.get("pool") if progress else "Unknown"

            if current_pool != from_pool:
                self.record_result(
                    f"Progression {from_pool} → {to_pool}",
                    False,
                    f"Expected pool {from_pool}, got {current_pool}"
                )
                continue

            # Practice
            resp = self.api_get("/api/practice/session")
            if not resp.json().get("available"):
                self.record_result(
                    f"Progression {from_pool} → {to_pool}",
                    False,
                    f"Practice not available"
                )
                continue

            exercises = resp.json().get("exercises", [])
            target_exercise = next((e for e in exercises if e.get("word_id") == word_id), None)

            if not target_exercise:
                self.record_result(
                    f"Progression {from_pool} → {to_pool}",
                    False,
                    f"Word not in practice session"
                )
                continue

            # Verify exercise type
            actual_type = target_exercise.get("type")
            type_matches = actual_type == expected_type

            # Submit correct answer
            answers = [{"word_id": e["word_id"], "correct": True} for e in exercises]
            resp = self.api_post("/api/practice/submit", {"answers": answers})

            result = next((r for r in resp.json().get("results", []) if r.get("word_id") == word_id), None)

            pool_correct = result and result.get("new_pool") == to_pool

            self.record_result(
                f"Progression {from_pool} → {to_pool} (type: {expected_type})",
                pool_correct and type_matches,
                f"new_pool: {result.get('new_pool') if result else 'None'}, type: {actual_type}, expected_type: {expected_type}"
            )

    def test_13_daily_limit(self):
        """Test daily learn limit (50 words)."""
        print(f"\n{Colors.BOLD}Test 13: Daily Learn Limit (50 words){Colors.RESET}")

        # Reset and create fresh user
        self.reset_test_data()
        resp = requests.post(f"{self.base_url}/api/auth/login", json={"username": "limit_test_user"})
        self.user_id = resp.json().get("id")

        # Get word IDs directly from DB
        word_ids = self.get_word_ids_from_db(55)

        # Create 50 word progress records as learned today
        today = datetime.now(timezone.utc).replace(hour=1, minute=0, second=0, microsecond=0)

        for i, word_id in enumerate(word_ids[:50]):
            self.execute_sql(
                """
                INSERT INTO word_progress (id, user_id, word_id, pool, learned_at, next_available_time, is_in_review_phase)
                VALUES (gen_random_uuid(), %s, %s::uuid, 'P1', %s, %s, FALSE)
                """,
                (self.user_id, word_id, today, today + timedelta(minutes=10))
            )

        # Check stats
        stats = self.api_get("/api/home/stats").json()

        self.record_result(
            "Today learned count is 50",
            stats.get("today_learned") == 50,
            f"today_learned: {stats.get('today_learned')}"
        )

        self.record_result(
            "Can learn is False (daily limit reached)",
            stats.get("can_learn") == False,
            f"can_learn: {stats.get('can_learn')}"
        )

        # Try to get learn session
        resp = self.api_get("/api/learn/session")
        data = resp.json()

        self.record_result(
            "Learn session returns daily_limit_reached",
            data.get("available") == False and data.get("reason") == "daily_limit_reached",
            f"available: {data.get('available')}, reason: {data.get('reason')}"
        )

    def test_14_p1_pool_limit(self):
        """Test P1 pool limit (10 words upcoming)."""
        print(f"\n{Colors.BOLD}Test 14: P1 Pool Limit (10 words){Colors.RESET}")

        # Reset and create fresh user
        self.reset_test_data()
        resp = requests.post(f"{self.base_url}/api/auth/login", json={"username": "p1_limit_test_user"})
        self.user_id = resp.json().get("id")

        # Get word IDs directly from DB
        word_ids = self.get_word_ids_from_db(15)

        # Create 10 P1 words with next_available_time within 10 minutes
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)  # learned_at is yesterday so it doesn't count toward daily limit

        for i, word_id in enumerate(word_ids[:10]):
            self.execute_sql(
                """
                INSERT INTO word_progress (id, user_id, word_id, pool, learned_at, next_available_time, is_in_review_phase)
                VALUES (gen_random_uuid(), %s, %s::uuid, 'P1', %s, %s, FALSE)
                """,
                (self.user_id, word_id, yesterday, now + timedelta(minutes=5))  # 5 minutes from now
            )

        # Check stats
        stats = self.api_get("/api/home/stats").json()

        self.record_result(
            "Can learn is False (P1 pool full)",
            stats.get("can_learn") == False,
            f"can_learn: {stats.get('can_learn')}"
        )

        # Try to get learn session
        resp = self.api_get("/api/learn/session")
        data = resp.json()

        self.record_result(
            "Learn session returns p1_pool_full",
            data.get("available") == False and data.get("reason") == "p1_pool_full",
            f"available: {data.get('available')}, reason: {data.get('reason')}"
        )

    def _ensure_practice_available(self):
        """Ensure enough words are available for practice."""
        # Learn more words if needed
        for _ in range(2):
            resp = self.api_get("/api/learn/session")
            if resp.json().get("available"):
                word_ids = [w["id"] for w in resp.json().get("words", [])]
                self.api_post("/api/learn/complete", {"word_ids": word_ids})
                for wid in word_ids:
                    self.set_word_time(wid, -1)

    def run_all_tests(self):
        """Run all integration tests."""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Coach Vocabulary Integration Tests{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

        try:
            # Setup
            self.setup_db()
            self.reset_test_data()

            # Run tests
            self.test_01_login()
            self.test_02_initial_stats()
            self.test_03_learn_session()
            self.test_04_practice_not_available_yet()
            self.test_05_practice_after_time()
            self.test_06_practice_answer_correct()
            self.test_07_practice_answer_wrong()
            self.test_08_review_session()
            self.test_09_review_complete()
            self.test_10_r_pool_practice_correct()
            self.test_11_r_pool_practice_wrong()
            self.test_12_p_pool_full_progression()
            self.test_13_daily_limit()
            self.test_14_p1_pool_limit()

        except Exception as e:
            print(f"\n{Colors.RED}Error during tests: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
        finally:
            self.teardown_db()

        # Print summary and return success status
        return self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

        passed = sum(1 for t in self.test_results if t.result == TestResult.PASS)
        failed = sum(1 for t in self.test_results if t.result == TestResult.FAIL)
        skipped = sum(1 for t in self.test_results if t.result == TestResult.SKIP)
        total = len(self.test_results)

        print(f"\n  Total:   {total}")
        print(f"  {Colors.GREEN}Passed:  {passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed:  {failed}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Skipped: {skipped}{Colors.RESET}")

        if failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.RESET}")
            for t in self.test_results:
                if t.result == TestResult.FAIL:
                    print(f"  - {t.name}: {t.message}")

        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")

        return failed == 0


def check_server():
    """Check if test server is running."""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def main():
    print(f"{Colors.BLUE}Checking test server...{Colors.RESET}")

    if not check_server():
        print(f"{Colors.RED}Test server not running!{Colors.RESET}")
        print(f"\nPlease start the test server first:")
        print(f"  DATABASE_URL=postgresql://ianchen@localhost:5432/coach_vocabulary_test \\")
        print(f"      uvicorn app.main:app --port 8001")
        sys.exit(1)

    print(f"{Colors.GREEN}Test server is running{Colors.RESET}")

    test = IntegrationTest()
    success = test.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
