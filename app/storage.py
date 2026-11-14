from dataclasses import asdict
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
import json
import os
import sqlite3

from .domain import Draw, canonical, digest, snapshot_hash, utc_now, validate_draw, validate_ticket
from .rules import get_rule
from .paths import installed_data


def data_directory():
    if installed_data() is not None:
        return installed_data()
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
    return base / "VietlottDesktop"


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_directory()/"history.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 2:
            self.db.close(); raise ValueError("Database của phiên bản mới hơn; không hạ cấp hoặc ghi đè.")
        if version == 0:
            if self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                backup_path = self.path.with_suffix(".pre-v1.sqlite3")
                if backup_path.exists():
                    self.db.close(); raise ValueError("Backup migration đã tồn tại; cần kiểm tra trước khi tiếp tục.")
                with closing(sqlite3.connect(backup_path)) as backup:
                    self.db.backup(backup)
            self.db.executescript("""
                BEGIN;
                CREATE TABLE IF NOT EXISTS rule_versions (
                    game_id TEXT, mode_id TEXT, rule_version TEXT, body TEXT NOT NULL,
                    PRIMARY KEY(game_id,mode_id,rule_version));
                CREATE TABLE IF NOT EXISTS draw_revisions (
                    game_id TEXT, mode_id TEXT, draw_id TEXT, revision INTEGER,
                    rule_version TEXT NOT NULL, draw_at_utc TEXT NOT NULL,
                    content_hash TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY(game_id,mode_id,draw_id,revision));
                CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY, game_id TEXT NOT NULL, mode_id TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL, target_draw_id TEXT NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id INTEGER PRIMARY KEY, created_at_utc TEXT NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS data_snapshots (hash TEXT PRIMARY KEY, body TEXT NOT NULL);
                PRAGMA user_version=2;
                COMMIT;
            """)

        elif version == 1:
            backup_path = self.path.with_suffix(".pre-v2.sqlite3")
            if backup_path.exists():
                self.db.close(); raise ValueError("Backup pre-v2 đã tồn tại; cần kiểm tra trước khi migration.")
            with closing(sqlite3.connect(backup_path)) as backup:
                self.db.backup(backup)
            self.db.executescript("""
                BEGIN;
                CREATE TABLE data_snapshots (hash TEXT PRIMARY KEY, body TEXT NOT NULL);
                PRAGMA user_version=2;
                COMMIT;
            """)

        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS sync_continuity (
                game_id TEXT, mode_id TEXT, rule_version TEXT, fingerprint TEXT NOT NULL,
                PRIMARY KEY(game_id,mode_id,rule_version));
            CREATE TABLE IF NOT EXISTS auto_update_runs (
                game_id TEXT, day TEXT, status TEXT NOT NULL, message TEXT NOT NULL,
                PRIMARY KEY(game_id,day));
        """)

    def close(self):
        self.db.close()

    @staticmethod
    def _check_limit(limit):
        if type(limit) is not int or not 1 <= limit <= 2000:
            raise ValueError("Giới hạn lịch sử phải từ 1 đến 2000 kỳ.")

    def sync_window(self, rule, limit):
        self._check_limit(limit)
        draws = self.list_draws(rule)
        row = self.db.execute("SELECT fingerprint FROM sync_continuity WHERE game_id=? AND mode_id=? AND rule_version=?",
                              (rule.game_id, rule.mode_id, rule.rule_version)).fetchone()
        if len(draws) < limit or not row or row[0] != digest([asdict(d) for d in draws]):
            return []
        return draws

    def add_draws(self, rule, draws, *, keep_latest=None, check_cancel=None):
        with self.db:
            if not self.db.in_transaction:
                self.db.execute("BEGIN IMMEDIATE")
            return self._add_draws(rule, draws, keep_latest=keep_latest, check_cancel=check_cancel)

    def _add_draws(self, rule, draws, *, keep_latest=None, check_cancel=None):
        draws = list(draws)
        check = check_cancel or (lambda: None)
        check()
        if keep_latest is not None:
            self._check_limit(keep_latest)
            if not draws:
                raise ValueError("Không thu gọn lịch sử bằng batch rỗng.")
        for draw in draws:
            validate_draw(rule, draw)
            check()
        counts = {"added": 0, "revised": 0, "unchanged": 0}
        self.db.execute("INSERT OR IGNORE INTO rule_versions VALUES (?,?,?,?)",
                        (rule.game_id, rule.mode_id, rule.rule_version, canonical(asdict(rule))))
        for draw in draws:
            check()
            content_hash = digest({"payload": draw.payload, "draw_at_utc": draw.draw_at_utc,
                                   "rule_version": draw.rule_version})
            latest = self.db.execute("SELECT revision,content_hash FROM draw_revisions WHERE game_id=? AND mode_id=? AND draw_id=? ORDER BY revision DESC LIMIT 1",
                                     (draw.game_id, draw.mode_id, draw.draw_id)).fetchone()
            if latest and latest["content_hash"] == content_hash:
                counts["unchanged"] += 1; continue
            revision = latest["revision"]+1 if latest else 1
            body = asdict(draw); body["revision"] = revision
            self.db.execute("INSERT INTO draw_revisions VALUES (?,?,?,?,?,?,?,?)",
                (draw.game_id, draw.mode_id, draw.draw_id, revision, draw.rule_version,
                 draw.draw_at_utc, content_hash, canonical(body)))
            counts["revised" if latest else "added"] += 1
        check()
        scope = (rule.game_id, rule.mode_id, rule.rule_version)
        self.db.execute("DELETE FROM sync_continuity WHERE game_id=? AND mode_id=? AND rule_version=?", scope)
        if keep_latest is not None:
            current = self.list_draws(rule)
            for draw in current[:-keep_latest]:
                check()
                self.db.execute("DELETE FROM draw_revisions WHERE game_id=? AND mode_id=? AND rule_version=? AND draw_id=?",
                                (*scope, draw.draw_id))
            retained = self.list_draws(rule)
            self.db.execute("INSERT INTO sync_continuity VALUES (?,?,?,?)",
                            (*scope, digest([asdict(d) for d in retained])))
        check()
        return counts

    def apply_sync(self, rule, receipt, limit, check_cancel=None):
        return self.apply_sync_many([(rule, receipt)], limit, check_cancel=check_cancel)[0]

    def apply_sync_many(self, batches, limit, check_cancel=None):
        self._check_limit(limit)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            return [self._apply_sync(rule, receipt, limit, check_cancel=check_cancel)
                    for rule, receipt in batches]

    def _apply_sync(self, rule, receipt, limit, check_cancel=None):
        self._check_limit(limit)
        if not isinstance(receipt, dict):
            raise ValueError("Biên nhận cập nhật không hợp lệ.")
        status = receipt.get("status")
        if status in {"incomplete", "cancelled", "failed", "error"}:
            raise ValueError("Lần tải chưa hoàn tất; giữ nguyên lịch sử.")
        draws = list(receipt.get("draws", ()))
        complete = status in {"requested_limit", "source_boundary", "known_boundary"}
        if complete and (not draws or len({d.draw_id for d in draws}) != len(draws)):
            raise ValueError("Batch hoàn tất phải có kết quả và mã kỳ duy nhất.")
        if status == "requested_limit" and len(draws) < limit:
            raise ValueError("Batch chưa đủ phạm vi lịch sử yêu cầu.")
        if status == "known_boundary":
            known = self.sync_window(rule, limit)
            if not known or not ({d.draw_id for d in known} & {d.draw_id for d in draws}):
                raise ValueError("Mất bằng chứng liên tục; cần tải lại đủ phạm vi.")
        return self._add_draws(rule, draws, keep_latest=limit if complete else None, check_cancel=check_cancel)

    @staticmethod
    def _auto_identity(game_id, day):
        get_rule(game_id)
        if isinstance(day, str):
            if len(day) == 10 and date.fromisoformat(day).isoformat() == day:
                return
            if len(day) == 16 and datetime.fromisoformat(day).isoformat(" ", timespec="minutes") == day:
                return
        raise ValueError("Ngày hoặc giờ chạy tự động không hợp lệ.")

    def claim_auto_update(self, game_id, day):
        self._auto_identity(game_id, day)
        with self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO auto_update_runs VALUES (?,?,'running','')", (game_id, day))
        return cursor.rowcount == 1

    def finish_auto_update(self, game_id, day, status, message):
        self._auto_identity(game_id, day)
        if not isinstance(status, str) or not status or not isinstance(message, str):
            raise ValueError("Trạng thái chạy tự động không hợp lệ.")
        with self.db:
            self.db.execute("UPDATE auto_update_runs SET status=?,message=? WHERE game_id=? AND day=?",
                            (status, message, game_id, day))

    def auto_update_runs(self, *, latest_only=False):
        query = "SELECT game_id,day,status,message FROM auto_update_runs"
        if latest_only:
            query += " WHERE (game_id, day) IN (SELECT game_id, MAX(day) FROM auto_update_runs GROUP BY game_id)"
        return [dict(row) for row in self.db.execute(query + " ORDER BY day DESC,game_id")]

    def list_draws(self, rule):
        rows = self.db.execute("""
            SELECT d.body FROM draw_revisions d
            WHERE d.game_id=? AND d.mode_id=? AND d.rule_version=?
              AND d.revision=(SELECT MAX(x.revision) FROM draw_revisions x
                 WHERE x.game_id=d.game_id AND x.mode_id=d.mode_id AND x.draw_id=d.draw_id)
            ORDER BY d.draw_at_utc, CAST(d.draw_id AS INTEGER), d.draw_id
        """, (rule.game_id, rule.mode_id, rule.rule_version)).fetchall()
        return [Draw(**json.loads(row[0])) for row in rows]

    def revisions(self, game_id, mode_id, draw_id):
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT body FROM draw_revisions WHERE game_id=? AND mode_id=? AND draw_id=? ORDER BY revision",
            (game_id, mode_id, draw_id))]

    def snapshot(self, rule, draws=None):
        records = self.list_draws(rule) if draws is None else list(draws)
        for draw in records:
            validate_draw(rule, draw)
        if len({draw.draw_id for draw in records}) != len(records):
            raise ValueError("Snapshot không được chứa nhiều phiên bản cùng kỳ.")
        body = [asdict(d) for d in records]
        snapshot = {"hash": snapshot_hash(asdict(rule), body), "draws": body, "rule": asdict(rule)}
        self._save_snapshot(snapshot)
        return snapshot

    def _save_snapshot(self, snapshot):
        if snapshot["hash"] != snapshot_hash(snapshot["rule"], snapshot["draws"]):
            raise ValueError("Hash snapshot không khớp nội dung.")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO data_snapshots VALUES (?,?)", (snapshot["hash"], canonical(snapshot)))

    def get_snapshot(self, snapshot_hash):
        row = self.db.execute("SELECT body FROM data_snapshots WHERE hash=?", (snapshot_hash,)).fetchone()
        if not row:
            raise ValueError("Không tìm thấy snapshot đã lưu.")
        return json.loads(row[0])

    def _snapshot_stale(self, snapshot_hash):
        if not snapshot_hash:
            return None
        try:
            snapshot = self.get_snapshot(snapshot_hash)
        except ValueError:
            return None
        for draw in snapshot["draws"]:
            row = self.db.execute("SELECT MAX(revision) FROM draw_revisions WHERE game_id=? AND mode_id=? AND draw_id=?",
                                  (draw["game_id"], draw["mode_id"], draw["draw_id"])).fetchone()
            if row[0] != draw["revision"]:
                return True
        return False

    def save_suggestions(self, rule, tickets, target_draw_id, method, snapshot, metadata=None):
        if not isinstance(target_draw_id, str) or not target_draw_id.strip():
            raise ValueError("Cần mã kỳ đích; không tự suy từ kỳ mới nhất.")
        for item in snapshot["draws"]:
            previous_id = item["draw_id"]
            if previous_id == target_draw_id or (previous_id.isdigit() and target_draw_id.isdigit() and int(previous_id) >= int(target_draw_id)):
                raise ValueError("Gợi ý kỳ tương lai không được dùng lịch sử của kỳ đích hoặc kỳ sau nó.")
        for ticket in tickets:
            validate_ticket(rule, ticket)
        self._save_snapshot(snapshot)
        created = utc_now()
        with self.db:
            for ticket in tickets:
                body = {"ticket": asdict(ticket), "method": method, "snapshot_hash": snapshot["hash"],
                        "history_count": len(snapshot["draws"]), "created_at_utc": created,
                        "target_draw_id": target_draw_id, "saved_before_draw": None,
                        "note": "Chưa biết giờ khóa kỳ đích; không chứng nhận lưu trước giờ quay."}
                if metadata is not None:
                    body["metadata"] = metadata
                self.db.execute("INSERT INTO suggestions(game_id,mode_id,created_at_utc,target_draw_id,body) VALUES (?,?,?,?,?)",
                                (rule.game_id, rule.mode_id, created, target_draw_id, canonical(body)))

    def suggestions(self, rule):
        records = [json.loads(row[0]) for row in self.db.execute(
            "SELECT body FROM suggestions WHERE game_id=? AND mode_id=? ORDER BY id DESC",
            (rule.game_id, rule.mode_id))]
        for record in records:
            record["stale"] = self._snapshot_stale(record.get("snapshot_hash"))
        return records

    def save_report(self, report):
        report = json.loads(canonical(report))
        manifest = report.get("manifest", {})
        snapshot = manifest.pop("input_snapshot", None)
        if snapshot:
            self._save_snapshot(snapshot)
            manifest["input_snapshot_hash"] = snapshot["hash"]
        if report.get("status") == "completed" and manifest.get("holdout_count", 0):
            prior = 0
            for previous in self.reports():
                old = previous.get("manifest", {})
                same_series = (old.get("game_id"), old.get("mode_id")) == (manifest.get("game_id"), manifest.get("mode_id"))
                overlap = bool(set(old.get("holdout_ids", [])) & set(manifest.get("holdout_ids", [])))
                if same_series and previous.get("status") == "completed" and old.get("holdout_count", 0) and (overlap or old.get("dataset_hash") == manifest.get("dataset_hash")):
                    prior += 1
            report["prior_holdout_runs"] = prior
            if prior:
                report["assessment"] = "exploratory_reused_holdout"
        with self.db:
            cursor = self.db.execute("INSERT INTO evaluation_runs(created_at_utc,body) VALUES (?,?)", (utc_now(), canonical(report)))
        return cursor.lastrowid

    def reports(self):
        records = [json.loads(row[0]) for row in self.db.execute("SELECT body FROM evaluation_runs ORDER BY id DESC")]
        for record in records:
            record["stale"] = self._snapshot_stale(record.get("manifest", {}).get("input_snapshot_hash"))
        return records
