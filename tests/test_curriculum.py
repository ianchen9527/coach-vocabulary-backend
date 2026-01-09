#!/usr/bin/env python3
"""
Integration Test for Curriculum (Levels & Categories)
"""

import json
import requests
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import psycopg2

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/coach_vocabulary_test"

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

class CurriculumTest:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.user_id: Optional[str] = None
        self.test_results: List[TestCase] = []
        self.db_connection = None

    def setup_db(self):
        """Connect to test database."""
        self.db_connection = psycopg2.connect(TEST_DB_URL)
        self.db_connection.autocommit = True

    def teardown_db(self):
        if self.db_connection:
            self.db_connection.close()

    def execute_sql(self, sql: str, params: tuple = None):
        with self.db_connection.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.description:
                return cursor.fetchall()
            return None

    def reset_test_data(self):
        """Reset users, progress, and words. Preserves levels/categories."""
        self.execute_sql("DELETE FROM word_progress")
        self.execute_sql("DELETE FROM users")
        self.execute_sql("DELETE FROM words")
        print(f"{Colors.BLUE}Test data reset{Colors.RESET}")

    def seed_test_words(self):
        """Seed specific words for testing curriculum flow."""
        # Need Levels: 1 (A1.1), 2 (A1.2)
        # Need Categories: 1 (Function Words), 2 (Basic Descriptors)
        # We will insert:
        # - 3 words in L1, C1
        # - 3 words in L1, C2
        # - 3 words in L2, C1
        
        words = [
            # L1, C1
            ("w1_1_1", "t1", 1, 1), ("w1_1_2", "t2", 1, 1), ("w1_1_3", "t3", 1, 1),
            # L1, C2
            ("w1_2_1", "t4", 1, 2), ("w1_2_2", "t5", 1, 2), ("w1_2_3", "t6", 1, 2),
            # L2, C1
            ("w2_1_1", "t7", 2, 1), ("w2_1_2", "t8", 2, 1), ("w2_1_3", "t9", 2, 1),
        ]
        
        for w, t, l, c in words:
            self.execute_sql(
                """
                INSERT INTO words (id, word, translation, level_id, category_id, created_at)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, NOW())
                """,
                (w, t, l, c)
            )
        print(f"{Colors.BLUE}Seeded {len(words)} test words{Colors.RESET}")

    def api_get(self, endpoint: str) -> requests.Response:
        headers = {"X-User-Id": self.user_id} if self.user_id else {}
        resp = requests.get(f"{self.base_url}{endpoint}", headers=headers)
        if resp.status_code >= 400:
            print(f"{Colors.RED}API GET Error {endpoint}: {resp.status_code}\n{resp.text}{Colors.RESET}")
        return resp

    def api_post(self, endpoint: str, data: Dict = None) -> requests.Response:
        headers = {"X-User-Id": self.user_id, "Content-Type": "application/json"} if self.user_id else {"Content-Type": "application/json"}
        resp = requests.post(f"{self.base_url}{endpoint}", headers=headers, json=data)
        if resp.status_code >= 400:
            print(f"{Colors.RED}API POST Error {endpoint}: {resp.status_code}\n{resp.text}{Colors.RESET}")
        return resp

    def record_result(self, name: str, passed: bool, message: str = ""):
        result = TestResult.PASS if passed else TestResult.FAIL
        self.test_results.append(TestCase(name, result, message))
        color = Colors.GREEN if passed else Colors.RED
        status = "PASS" if passed else "FAIL"
        print(f"  {color}[{status}]{Colors.RESET} {name}")
        if message and not passed:
            print(f"         {Colors.YELLOW}{message}{Colors.RESET}")

    def run(self):
        try:
            self.setup_db()
            self.reset_test_data()
            self.seed_test_words()
            
            # 1. Login
            print(f"\n{Colors.BOLD}Test 1: Setup & Login{Colors.RESET}")
            resp = requests.post(f"{self.base_url}/api/auth/login", json={"username": "curriculum_test"})
            data = resp.json()
            self.user_id = data.get("id")
            
            # Verify initial level/category
            # Should now be None
            user_row = self.execute_sql("SELECT current_level_id, current_category_id FROM users WHERE id = %s", (self.user_id,))
            self.record_result(
                "Initial Level/Category is None",
                user_row and user_row[0][0] is None and user_row[0][1] is None,
                f"Got: {user_row}"
            )

            # 2. Fetch Session (Should FAIL initially)
            print(f"\n{Colors.BOLD}Test 2: Fetch Session (Expect Error){Colors.RESET}")
            resp = self.api_get("/api/learn/session")
            self.record_result(
                "Session fails without level analysis",
                resp.status_code == 400,
                f"Status: {resp.status_code}, Body: {resp.text}"
            )
            
            # 2.1 Perform Level Analysis
            print(f"\n{Colors.BOLD}Test 2.1: Submit Level Analysis{Colors.RESET}")
            # Submit level 1
            resp = self.api_post("/api/level-analysis/submit", {"level_order": 1})
            self.record_result("Submit Level Analysis success", resp.status_code == 200)

            # 2.2 Fetch Session (Should SUCCEED now)
            # We have 3 words in L1 C1. Session size is 5.
            # It should fetch 3 from L1 C1, then 2 from L1 C2.
            print(f"\n{Colors.BOLD}Test 2.2: Fetch Session (After Analysis){Colors.RESET}")
            resp = self.api_get("/api/learn/session")
            data = resp.json()
            words = data.get("words", [])
            
            self.record_result("Session size is 5", len(words) == 5, f"Size: {len(words)}")
            
            # Check composition
            l1c1_count = sum(1 for w in words if w['word'].startswith('w1_1_'))
            l1c2_count = sum(1 for w in words if w['word'].startswith('w1_2_'))
            
            self.record_result(
                "Fetched 3 from L1C1 and 2 from L1C2",
                l1c1_count == 3 and l1c2_count == 2,
                f"L1C1: {l1c1_count}, L1C2: {l1c2_count}"
            )
            
            # 3. Complete Session & Advancements
            # The highest word learned is from L1 C2. User should advance to L1 C2.
            print(f"\n{Colors.BOLD}Test 3: Complete & Advance{Colors.RESET}")
            word_ids = [w['id'] for w in words]
            resp = self.api_post("/api/learn/complete", {"word_ids": word_ids})
            
            self.record_result("Complete success", resp.json().get("success") == True)
            
            # Verify user update
            user_row = self.execute_sql("SELECT current_level_id, current_category_id FROM users WHERE id = %s", (self.user_id,))
            self.record_result(
                "User advanced to L1 C2",
                user_row and user_row[0][0] == 1 and user_row[0][1] == 2,
                f"Got: {user_row}"
            )
            
            # 4. Fetch Next Session (Rollover Level)
            # Remaining: 1 word in L1 C2 ("w1_2_3"), 3 words in L2 C1 ("w2_1_...").
            # Total 4 available. Session might return 4 if P0 exhausted?
            # Or if it strictly requires 5, it returns what it can.
            
            print(f"\n{Colors.BOLD}Test 4: Fetch Session (Rollover Level){Colors.RESET}")
            resp = self.api_get("/api/learn/session")
            data = resp.json()
            words = data.get("words", [])
            
            # Depending on if we have more words. We seeded 9 total. Learned 5. Remaining 4.
            # Return size should be 4.
            self.record_result("Session size is 4 (exhausted)", len(words) == 4, f"Size: {len(words)}")
            
            l1c2_rem = sum(1 for w in words if w['word'].startswith('w1_2_')) # Should be 1
            l2c1_cnt = sum(1 for w in words if w['word'].startswith('w2_1_')) # Should be 3
            
            self.record_result(
                "Fetched remaining L1C2 and L2C1",
                l1c2_rem == 1 and l2c1_cnt == 3,
                f"L1C2: {l1c2_rem}, L2C1: {l2c1_cnt}"
            )
            
            # 5. Complete & Advance to Level 2
            print(f"\n{Colors.BOLD}Test 5: Advance to Level 2{Colors.RESET}")
            word_ids = [w['id'] for w in words]
            self.api_post("/api/learn/complete", {"word_ids": word_ids})
            
            user_row = self.execute_sql("SELECT current_level_id, current_category_id FROM users WHERE id = %s", (self.user_id,))
            self.record_result(
                "User advanced to L2 C1",
                user_row and user_row[0][0] == 2 and user_row[0][1] == 1,
                f"Got: {user_row}"
            )

        finally:
            self.teardown_db()

        # Summary
        passed = sum(1 for t in self.test_results if t.result == TestResult.PASS)
        total = len(self.test_results)
        print(f"\n{Colors.BOLD}Summary: {passed}/{total} Passed{Colors.RESET}")
        if passed != total:
            sys.exit(1)

if __name__ == "__main__":
    CurriculumTest().run()
