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
                error_message TEXT,
                user_script TEXT,
                sd_model_id TEXT,
                voice_id TEXT,
                tts_exaggeration REAL DEFAULT 0.5,
                tts_cfg_weight REAL DEFAULT 0.5,
                tts_speed REAL DEFAULT 1.0,
                effect_ids TEXT DEFAULT '["ken_burns"]',
                caption_style TEXT DEFAULT 'chunked'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                scene_index INTEGER NOT NULL,
                narration_text TEXT NOT NULL,
                narration_audio TEXT,
                image_prompt TEXT NOT NULL,
                edited_text TEXT,
                edited_tags TEXT,
                edited_audio TEXT,
                image_path TEXT,
                audio_path TEXT,
                duration_seconds REAL,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS image_pool (
                id TEXT PRIMARY KEY,
                image_tags TEXT NOT NULL,
                file_path TEXT NOT NULL,
                source_job_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sd_models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                model_key TEXT NOT NULL,
                sampler_name TEXT DEFAULT 'dpmpp_2m',
                num_inference_steps INTEGER DEFAULT 40,
                guidance_scale REAL DEFAULT 7.5,
                vram_usage_level TEXT DEFAULT 'balanced',
                clip_skip BOOLEAN DEFAULT 0,
                is_default BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS outline (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                chapter_index INTEGER NOT NULL,
                section_index INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL DEFAULT 'chapter',
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)
        # Schema Migration: Add columns to existing tables if they omit them
        migration_queries = [
            "ALTER TABLE jobs ADD COLUMN workflow_mode TEXT NOT NULL DEFAULT 'basic'",
            "ALTER TABLE jobs ADD COLUMN approved_script BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE jobs ADD COLUMN approved_visuals BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE scenes ADD COLUMN edited_text TEXT",
            "ALTER TABLE scenes ADD COLUMN edited_tags TEXT",
            "ALTER TABLE scenes ADD COLUMN narration_audio TEXT",
            "ALTER TABLE scenes ADD COLUMN edited_audio TEXT",
            "ALTER TABLE jobs ADD COLUMN user_script TEXT",
            "ALTER TABLE jobs ADD COLUMN sd_model_id TEXT",
            "ALTER TABLE jobs ADD COLUMN voice_id TEXT",
            "ALTER TABLE jobs ADD COLUMN tts_exaggeration REAL DEFAULT 0.5",
            "ALTER TABLE jobs ADD COLUMN tts_cfg_weight REAL DEFAULT 0.5",
            "ALTER TABLE jobs ADD COLUMN tts_speed REAL DEFAULT 1.0",
            "ALTER TABLE jobs ADD COLUMN effect_ids TEXT DEFAULT '[\"ken_burns\"]'",
            "ALTER TABLE jobs ADD COLUMN caption_style TEXT DEFAULT 'chunked'",
        ]
        
        for query in migration_queries:
            try:
                await db.execute(query)
            except aiosqlite.OperationalError:
                # Column likely already exists
                pass
            
        await db.commit()


# --- Job Operations ---

async def create_job(
    topic: str, 
    video_type: str, 
    voice_type: str = "female", 
    workflow_mode: str = "basic", 
    user_script: str | None = None,
    sd_model_id: str | None = None,
    voice_id: str | None = None,
    tts_exaggeration: float = 0.5,
    tts_cfg_weight: float = 0.5,
    tts_speed: float = 1.0,
    effect_ids: str = '["ken_burns"]',
    caption_style: str = "chunked"
) -> dict:
    """Create a new job and return it."""
    job_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO jobs (
                   id, topic, video_type, voice_type, workflow_mode, user_script, 
                   status, progress_pct, created_at,
                   sd_model_id, voice_id, tts_exaggeration, tts_cfg_weight, tts_speed, effect_ids, caption_style
               )
               VALUES (?, ?, ?, ?, ?, ?, 'queued', 0, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id, topic, video_type, voice_type, workflow_mode, user_script, 
                now,
                sd_model_id, voice_id, tts_exaggeration, tts_cfg_weight, tts_speed, effect_ids, caption_style
            )
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
               WHERE status IN ('queued', 'generating_script', 'generating_outline', 'expanding_scenes', 'revising_script', 'generating_images', 'generating_audio', 'assembling', 'adding_captions')"""
        )
        await db.commit()


# --- Scene Operations ---

async def create_scenes(job_id: str, scenes: list[dict]):
    """Bulk insert scenes for a job."""
    async with aiosqlite.connect(DB_PATH) as db:
        for i, scene in enumerate(scenes):
            scene_id = f"{job_id}-s{i:03d}"
            n_audio = scene.get("narration_audio", scene.get("narration_text", ""))
            await db.execute(
                """INSERT INTO scenes (id, job_id, scene_index, narration_text, narration_audio, image_prompt)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (scene_id, job_id, i, scene["narration_text"], n_audio, scene["image_prompt"])
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


async def delete_scenes_for_job(job_id: str):
    """Delete all scenes associated with a job."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM scenes WHERE job_id = ?", (job_id,))
        await db.commit()


# --- Image Pool Operations ---

async def add_to_image_pool(image_tags: str, file_path: str, source_job_id: str):
    """Add a generated image to the global pool for future reuse."""
    pool_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO image_pool (id, image_tags, file_path, source_job_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (pool_id, image_tags, file_path, source_job_id, now)
        )
        await db.commit()

async def get_all_pool_images() -> list[dict]:
    """Retrieve all images from the global pool for similarity matching."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM image_pool ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# --- Outline Operations ---

async def create_outline_items(job_id: str, chapters: list[dict]):
    """Bulk insert chapters and sections for a job's outline."""
    async with aiosqlite.connect(DB_PATH) as db:
        for ch_idx, chapter in enumerate(chapters):
            ch_id = f"{job_id}-ch{ch_idx:02d}"
            await db.execute(
                """INSERT INTO outline (id, job_id, chapter_index, section_index, title, description, type)
                   VALUES (?, ?, ?, NULL, ?, ?, 'chapter')""",
                (ch_id, job_id, ch_idx, chapter["title"], chapter.get("description", ""))
            )
            for sec_idx, section in enumerate(chapter.get("sections", [])):
                sec_id = f"{job_id}-ch{ch_idx:02d}-s{sec_idx:02d}"
                await db.execute(
                    """INSERT INTO outline (id, job_id, chapter_index, section_index, title, description, type)
                       VALUES (?, ?, ?, ?, ?, ?, 'section')""",
                    (sec_id, job_id, ch_idx, sec_idx, section["title"], section.get("description", ""))
                )
        await db.commit()


async def get_outline(job_id: str) -> list[dict]:
    """Get all outline items for a job, ordered by chapter then section."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM outline WHERE job_id = ? ORDER BY chapter_index, section_index", (job_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_outline_item(item_id: str, **kwargs):
    """Update outline item fields dynamically."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [item_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE outline SET {set_clause} WHERE id = ?", values
        )
        await db.commit()


async def delete_outline_for_job(job_id: str):
    """Delete all outline items associated with a job."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM outline WHERE job_id = ?", (job_id,))
        await db.commit()


# --- SD Model Operations ---

async def get_sd_models() -> list[dict]:
    """Get all configured SD models."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sd_models ORDER BY name ASC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_sd_model(model_id: str) -> dict | None:
    """Get a single SD model configuration."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sd_models WHERE id = ?", (model_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_sd_model(name: str, model_key: str, **kwargs) -> dict:
    """Create a new SD model configuration."""
    model_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    
    # Extract optional fields with defaults mapped to schema
    sampler = kwargs.get("sampler_name", "dpmpp_2m")
    steps = kwargs.get("num_inference_steps", 40)
    guidance = kwargs.get("guidance_scale", 7.5)
    vram = kwargs.get("vram_usage_level", "balanced")
    clip_skip = 1 if kwargs.get("clip_skip", False) else 0
    is_default = 1 if kwargs.get("is_default", False) else 0

    async with aiosqlite.connect(DB_PATH) as db:
        if is_default:
            # Unset default on others
            await db.execute("UPDATE sd_models SET is_default = 0")
            
        await db.execute(
            """INSERT INTO sd_models (
                   id, name, model_key, sampler_name, num_inference_steps, 
                   guidance_scale, vram_usage_level, clip_skip, is_default, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (model_id, name, model_key, sampler, steps, guidance, vram, clip_skip, is_default, now)
        )
        await db.commit()
    
    # Return the created record by re-fetching
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sd_models WHERE id = ?", (model_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row)

async def update_sd_model(model_id: str, **kwargs):
    """Update SD model configuration."""
    if not kwargs:
        return
        
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [model_id]
    
    async with aiosqlite.connect(DB_PATH) as db:
        if kwargs.get("is_default", False):
            await db.execute("UPDATE sd_models SET is_default = 0 WHERE id != ?", (model_id,))
            
        await db.execute(f"UPDATE sd_models SET {set_clause} WHERE id = ?", values)
        await db.commit()

async def delete_sd_model(model_id: str):
    """Delete an SD model configuration."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sd_models WHERE id = ?", (model_id,))
        await db.commit()

