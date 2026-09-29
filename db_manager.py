import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class DatabaseManager:
    """
    isItCandidate ATS Veritabanı Yöneticisi.
    Hem PostgreSQL (kurumsal RDBMS) hem de SQLite (sıfır kurulumlu portatif) desteği sunar.
    """
    def __init__(
        self,
        db_type: str = "postgresql",
        pg_host: str = "127.0.0.1",
        pg_port: int = 5432,
        pg_database: str = "isitcandidate_db",
        pg_user: str = "postgres",
        pg_password: str = "",
        sqlite_path: str = "candidates_pool.db"
    ):
        self.db_type = db_type.lower()
        self.pg_config = {
            "host": pg_host,
            "port": pg_port,
            "database": pg_database,
            "user": pg_user,
            "password": pg_password
        }
        self.sqlite_path = sqlite_path
        self._active_backend = "sqlite"
        self.init_db()

    def _get_connection(self):
        """Veritabanı bağlantısı oluşturur; PostgreSQL başarısız olursa SQLite'a döner."""
        if self.db_type == "postgresql" and PSYCOPG2_AVAILABLE:
            try:
                conn = psycopg2.connect(**self.pg_config)
                self._active_backend = "postgresql"
                return conn
            except Exception as e:
                # PostgreSQL bağlantı hatasında güvenli SQLite fallback
                self._active_backend = "sqlite"
                conn = sqlite3.connect(self.sqlite_path)
                conn.row_factory = sqlite3.Row
                return conn
        else:
            self._active_backend = "sqlite"
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn

    @property
    def backend_name(self) -> str:
        return self._active_backend.upper()

    def init_db(self):
        """Tabloları ve indeksleri otomatik oluşturur."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if self._active_backend == "postgresql":
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS candidates (
                id SERIAL PRIMARY KEY,
                file_name VARCHAR(255),
                candidate_name VARCHAR(255) NOT NULL,
                current_title VARCHAR(255),
                experience_years VARCHAR(50),
                target_position VARCHAR(255) NOT NULL,
                suitability_score INTEGER NOT NULL,
                verdict VARCHAR(50) NOT NULL,
                policy_violation BOOLEAN DEFAULT FALSE,
                matched_requirements TEXT,
                missing_requirements TEXT,
                interview_questions TEXT,
                top_strengths TEXT,
                potential_risks TEXT,
                executive_summary TEXT,
                status VARCHAR(50) DEFAULT 'Yeni Başvuru',
                recruiter_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(suitability_score DESC);
            CREATE INDEX IF NOT EXISTS idx_candidates_verdict ON candidates(verdict);
            CREATE INDEX IF NOT EXISTS idx_candidates_position ON candidates(target_position);
            """
        else:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                candidate_name TEXT NOT NULL,
                current_title TEXT,
                experience_years TEXT,
                target_position TEXT NOT NULL,
                suitability_score INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                policy_violation BOOLEAN DEFAULT 0,
                matched_requirements TEXT,
                missing_requirements TEXT,
                interview_questions TEXT,
                top_strengths TEXT,
                potential_risks TEXT,
                executive_summary TEXT,
                status TEXT DEFAULT 'Yeni Başvuru',
                recruiter_notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(suitability_score DESC);
            CREATE INDEX IF NOT EXISTS idx_candidates_verdict ON candidates(verdict);
            """

        try:
            cursor.execute(create_table_sql)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def save_candidate(self, res: Dict[str, Any], target_position: str) -> int:
        """Bir aday değerlendirme sonucunu veritabanına kaydeder."""
        conn = self._get_connection()
        cursor = conn.cursor()

        matched_json = json.dumps(res.get("matched_requirements", []), ensure_ascii=False)
        missing_json = json.dumps(res.get("missing_or_gap_requirements", []), ensure_ascii=False)
        questions_json = json.dumps(res.get("tailored_interview_questions", []), ensure_ascii=False)
        strengths_json = json.dumps(res.get("top_strengths", []), ensure_ascii=False)
        risks_json = json.dumps(res.get("potential_risks", []), ensure_ascii=False)

        sql_pg = """
        INSERT INTO candidates (
            file_name, candidate_name, current_title, experience_years,
            target_position, suitability_score, verdict, policy_violation,
            matched_requirements, missing_requirements, interview_questions,
            top_strengths, potential_risks, executive_summary
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """

        sql_sqlite = """
        INSERT INTO candidates (
            file_name, candidate_name, current_title, experience_years,
            target_position, suitability_score, verdict, policy_violation,
            matched_requirements, missing_requirements, interview_questions,
            top_strengths, potential_risks, executive_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        values = (
            str(res.get("file_name", "CV.pdf")),
            str(res.get("candidate_name", "İsimsiz Aday")),
            str(res.get("current_title", "Belirtilmemiş")),
            str(res.get("experience_years", "-")),
            str(target_position),
            int(res.get("suitability_score", 50)),
            str(res.get("verdict", "YEDEK ADAY")),
            bool(res.get("policy_violation", False)),
            matched_json,
            missing_json,
            questions_json,
            strengths_json,
            risks_json,
            str(res.get("executive_summary", ""))
        )

        try:
            if self._active_backend == "postgresql":
                cursor.execute(sql_pg, values)
                inserted_id = cursor.fetchone()[0]
            else:
                cursor.execute(sql_sqlite, values)
                inserted_id = cursor.lastrowid
            conn.commit()
            return inserted_id
        finally:
            cursor.close()
            conn.close()

    def get_candidates(
        self,
        search_query: str = "",
        verdict_filter: str = "TÜMÜ",
        min_score: int = 0,
        position_filter: str = "TÜMÜ"
    ) -> List[Dict[str, Any]]:
        """Aday havuzunda gelişmiş SQL filtrelemesi gerçekleştirir."""
        conn = self._get_connection()
        cursor = conn.cursor()

        conditions = ["suitability_score >= %s" if self._active_backend == "postgresql" else "suitability_score >= ?"]
        params = [min_score]

        param_marker = "%s" if self._active_backend == "postgresql" else "?"

        if search_query.strip():
            wildcard = f"%{search_query.strip()}%"
            conditions.append(
                f"(candidate_name ILIKE {param_marker} OR current_title ILIKE {param_marker} OR matched_requirements ILIKE {param_marker})"
                if self._active_backend == "postgresql"
                else f"(candidate_name LIKE {param_marker} OR current_title LIKE {param_marker} OR matched_requirements LIKE {param_marker})"
            )
            params.extend([wildcard, wildcard, wildcard])

        if verdict_filter != "TÜMÜ":
            conditions.append(f"verdict = {param_marker}")
            params.append(verdict_filter)

        if position_filter != "TÜMÜ":
            conditions.append(f"target_position = {param_marker}")
            params.append(position_filter)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM candidates {where_clause} ORDER BY created_at DESC, suitability_score DESC;"

        try:
            cursor.execute(query, tuple(params))
            
            if self._active_backend == "postgresql":
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append(dict(zip(columns, row)))
            else:
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]

            # JSON alanlarını parse et
            for item in results:
                for json_field in ["matched_requirements", "missing_requirements", "interview_questions", "top_strengths", "potential_risks"]:
                    val = item.get(json_field)
                    if isinstance(val, str):
                        try:
                            item[json_field] = json.loads(val)
                        except:
                            item[json_field] = []
                    elif val is None:
                        item[json_field] = []
            return results
        finally:
            cursor.close()
            conn.close()

    def update_candidate_status(self, candidate_id: int, new_status: str, notes: str = None) -> bool:
        """Adayın ATS sürecindeki aşamasını günceller."""
        conn = self._get_connection()
        cursor = conn.cursor()
        param = "%s" if self._active_backend == "postgresql" else "?"

        if notes is not None:
            sql = f"UPDATE candidates SET status = {param}, recruiter_notes = {param} WHERE id = {param};"
            vals = (new_status, notes, candidate_id)
        else:
            sql = f"UPDATE candidates SET status = {param} WHERE id = {param};"
            vals = (new_status, candidate_id)

        try:
            cursor.execute(sql, vals)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def delete_candidate(self, candidate_id: int) -> bool:
        """Adayı veritabanından siler."""
        conn = self._get_connection()
        cursor = conn.cursor()
        param = "%s" if self._active_backend == "postgresql" else "?"
        sql = f"DELETE FROM candidates WHERE id = {param};"

        try:
            cursor.execute(sql, (candidate_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def get_unique_positions(self) -> List[str]:
        """Kayıtlı benzersiz pozisyon listesini döndürür."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT target_position FROM candidates ORDER BY target_position;")
            rows = cursor.fetchall()
            return [r[0] for r in rows if r[0]]
        except:
            return []
        finally:
            cursor.close()
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Genel veritabanı istatistiklerini hesaplar."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*), AVG(suitability_score) FROM candidates;")
            total_count, avg_score = cursor.fetchone() or (0, 0)

            cursor.execute("SELECT verdict, COUNT(*) FROM candidates GROUP BY verdict;")
            verdict_counts = dict(cursor.fetchall())

            cursor.execute("SELECT status, COUNT(*) FROM candidates GROUP BY status;")
            status_counts = dict(cursor.fetchall())

            return {
                "total_candidates": total_count or 0,
                "avg_score": round(avg_score or 0, 1),
                "verdicts": verdict_counts,
                "statuses": status_counts,
                "backend": self.backend_name
            }
        except:
            return {
                "total_candidates": 0,
                "avg_score": 0.0,
                "verdicts": {},
                "statuses": {},
                "backend": self.backend_name
            }
        finally:
            cursor.close()
            conn.close()
