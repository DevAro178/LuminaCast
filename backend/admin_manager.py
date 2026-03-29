"""
Admin Manager — SQLAdmin integration for database management.
"""
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DB_PATH

# SQLAdmin uses SQLAlchemy models. We define them here to match the aiosqlite schema.
Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    topic = Column(String)
    video_type = Column(String)
    voice_type = Column(String)
    status = Column(String)
    progress_pct = Column(Integer)
    total_scenes = Column(Integer)
    completed_scenes = Column(Integer)
    workflow_mode = Column(String)
    approved_script = Column(Boolean)
    approved_visuals = Column(Boolean)
    created_at = Column(String)
    completed_at = Column(String)
    output_path = Column(String)
    error_message = Column(Text)
    user_script = Column(Text)

class Scene(Base):
    __tablename__ = "scenes"
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    scene_index = Column(Integer)
    narration_text = Column(String)
    narration_audio = Column(String)
    image_prompt = Column(String)
    edited_text = Column(String)
    edited_tags = Column(String)
    edited_audio = Column(String)
    image_path = Column(String)
    audio_path = Column(String)
    duration_seconds = Column(Float)

class OutlineItem(Base):
    __tablename__ = "outline"
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    chapter_index = Column(Integer)
    section_index = Column(Integer)
    title = Column(String)
    description = Column(String)
    type = Column(String)

class ImagePool(Base):
    __tablename__ = "image_pool"
    id = Column(String, primary_key=True)
    image_tags = Column(String)
    file_path = Column(String)
    source_job_id = Column(String)
    created_at = Column(String)

# --- Admin Views ---

class JobAdmin(ModelView, model=Job):
    column_list = [Job.id, Job.topic, Job.status, Job.progress_pct, Job.created_at]
    column_searchable_list = [Job.id, Job.topic]
    column_filters = [Job.status, Job.workflow_mode]
    name = "Video Job"
    name_plural = "Video Jobs"
    icon = "fa-solid fa-list-check"

class SceneAdmin(ModelView, model=Scene):
    column_list = [Scene.job_id, Scene.scene_index, Scene.narration_text]
    column_searchable_list = [Scene.job_id, Scene.narration_text]
    name = "Scene"
    name_plural = "Scenes"
    icon = "fa-solid fa-clapperboard"

class OutlineAdmin(ModelView, model=OutlineItem):
    column_list = [OutlineItem.job_id, OutlineItem.chapter_index, OutlineItem.title, OutlineItem.type]
    name = "Outline Item"
    name_plural = "Outline Items"
    icon = "fa-solid fa-map-location-dot"

class ImagePoolAdmin(ModelView, model=ImagePool):
    column_list = [ImagePool.image_tags, ImagePool.source_job_id, ImagePool.created_at]
    name = "Global Image Pool"
    name_plural = "Global Image Pool"
    icon = "fa-solid fa-images"

def setup_admin(app: FastAPI):
    """Initialize SQLAdmin with models."""
    admin = Admin(app, engine, title="LuminaCast Admin")
    admin.add_view(JobAdmin)
    admin.add_view(SceneAdmin)
    admin.add_view(OutlineAdmin)
    admin.add_view(ImagePoolAdmin)
    return admin
