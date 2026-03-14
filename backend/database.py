"""
SQLite database setup and operations.
Uses aiosqlite for async compatibility with FastAPI.
"""
import aiosqlite
import uuid
from datetime import datetime, timezone
from config import DB_PATH


async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                video_type TEXT NOT NULL CHECK(video_type IN ('long', 'short')),
                voice_type TEXT NOT NULL DEFAULT 'female',
                status TEXT NOT NULL DEFAULT 'queued',
                progress_pct INTEGER NOT NULL DEFAULT 0,
                total_scenes INTEGER DEFAULT 0,
                completed_scenes INTEGER DEFAULT 0,
                workflow_mode TEXT NOT NULL DEFAULT 'basic',
                approved_script BOOLEAN NOT NULL DEFAULT 0,
                approved_visuals BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                output_path TEXT,
                error_message TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                scene_index INTEGER NOT NULL,
                narration_text TEXT NOT NULL,
                image_prompt TEXT NOT NULL,
                edited_text TEXT,
                edited_tags TEXT,
                image_path TEXT,
                audio_path TEXT,
                duration_seconds REAL,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)
        # Schema Migration: Add columns to existing tables if they omit them
        try:
            await db.execute("ALTER TABLE jobs ADD COLUMN workflow_mode TEXT NOT NULL DEFAULT 'basic'")
            await db.execute("ALTER TABLE jobs ADD COLUMN approved_script BOOLEAN NOT NULL DEFAULT 0")
            await db.execute("ALTER TABLE jobs ADD COLUMN approved_visuals BOOLEAN NOT NULL DEFAULT 0")
            await db.execute("ALTER TABLE scenes ADD COLUMN edited_text TEXT")
            await db.execute("ALTER TABLE scenes ADD COLUMN edited_tags TEXT")
        except aiosqlite.OperationalError:
            # Columns likely already exist
            pass
            
        await db.commit()


# --- Job Operations ---

async def create_job(topic: str, video_type: str, voice_type: str = "female", workflow_mode: str = "basic") -> dict:
    """Create a new job and return it."""
    job_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO jobs (id, topic, video_type, voice_type, workflow_mode, status, progress_pct, created_at)
               VALUES (?, ?, ?, ?, ?, 'queued', 0, ?)""",
            (job_id, topic, video_type, voice_type, workflow_mode, now)
        )
        await db.commit()
    return await get_job(job_id)


async def get_job(job_id: str) -> dict | None:
    """Get a single job by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_jobs(limit: int = 50) -> list[dict]:
    """List all jobs, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_job(job_id: str, **kwargs):
    """Update job fields dynamically."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE jobs SET {set_clause} WHERE id = ?", values
        )
        await db.commit()


async def mark_stuck_jobs_as_failed():
    """Mark any jobs not in a terminal state as failed (e.g., after server restart)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE jobs 
               SET status = 'failed', error_message = 'Job cancelled (server restarted)'
               WHERE status NOT IN ('completed', 'failed', 'error')"""
        )
        await db.commit()


# --- Scene Operations ---

async def create_scenes(job_id: str, scenes: list[dict]):
    """Bulk insert scenes for a job."""
    async with aiosqlite.connect(DB_PATH) as db:
        for i, scene in enumerate(scenes):
            scene_id = f"{job_id}-s{i:03d}"
            await db.execute(
                """INSERT INTO scenes (id, job_id, scene_index, narration_text, image_prompt)
                   VALUES (?, ?, ?, ?, ?)""",
                (scene_id, job_id, i, scene["narration_text"], scene["image_prompt"])
            )
        await db.execute(
            "UPDATE jobs SET total_scenes = ? WHERE id = ?",
            (len(scenes), job_id)
        )
        await db.commit()


async def get_scenes(job_id: str) -> list[dict]:
    """Get all scenes for a job, ordered by index."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM scenes WHERE job_id = ? ORDER BY scene_index", (job_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_scene(scene_id: str, **kwargs):
    """Update scene fields dynamically."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [scene_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE scenes SET {set_clause} WHERE id = ?", values
        )
        await db.commit()
