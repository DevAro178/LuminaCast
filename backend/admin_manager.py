"""
Admin Manager — SQLAdmin integration for database management.
"""
from fastapi import FastAPI
from sqladmin import Admin, ModelView
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import DB_PATH

# SQLAdmin uses SQLAlchemy models. We define them here to match the aiosqlite schema.
Base = declarative_base()
# Use 4 slashes for absolute paths on Linux if it starts with /, or 3 if it's relative.
# SQLAlchemy handles sqlite:///path/to/file.db correctly for absolute paths.
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def generate_id():
    return str(uuid.uuid4())[:8]

def generate_timestamp():
    return datetime.now(timezone.utc).isoformat()

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=generate_id)
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
    sd_model_id = Column(String)
    voice_id = Column(String)
    tts_exaggeration = Column(Float)
    tts_cfg_weight = Column(Float)
    tts_speed = Column(Float)
    effect_ids = Column(String)
    caption_style = Column(String)

    # Relationships
    scenes = relationship("Scene", back_populates="job", cascade="all, delete-orphan")
    outline_items = relationship("OutlineItem", back_populates="job", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"
    id = Column(String, primary_key=True, default=generate_id)
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

    job = relationship("Job", back_populates="scenes")

class OutlineItem(Base):
    __tablename__ = "outline"
    id = Column(String, primary_key=True, default=generate_id)
    job_id = Column(String, ForeignKey("jobs.id"))
    chapter_index = Column(Integer)
    section_index = Column(Integer)
    title = Column(String)
    description = Column(String)
    type = Column(String)

    job = relationship("Job", back_populates="outline_items")

class SdModel(Base):
    __tablename__ = "sd_models"
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String)
    model_key = Column(String)
    sampler_name = Column(String)
    num_inference_steps = Column(Integer)
    guidance_scale = Column(Float)
    vram_usage_level = Column(String)
    clip_skip = Column(Boolean)
    is_default = Column(Boolean)
    created_at = Column(String, default=generate_timestamp)

class ImagePool(Base):
    __tablename__ = "image_pool"
    id = Column(String, primary_key=True, default=generate_id)
    image_tags = Column(String)
    file_path = Column(String)
    source_job_id = Column(String)
    created_at = Column(String)

# --- Admin Views ---

class JobAdmin(ModelView, model=Job):
    column_list = [Job.id, Job.topic, Job.status, Job.progress_pct, Job.created_at]
    column_searchable_list = [Job.id, Job.topic]
    name = "Video Job"
    name_plural = "Video Jobs"
    icon = "fa-solid fa-list-check"
    category = "Production"

class SceneAdmin(ModelView, model=Scene):
    column_list = [Scene.job_id, Scene.scene_index, Scene.narration_text]
    column_searchable_list = [Scene.job_id, Scene.narration_text]
    name = "Scene"
    name_plural = "Scenes"
    icon = "fa-solid fa-clapperboard"
    category = "Production"

class OutlineAdmin(ModelView, model=OutlineItem):
    column_list = [OutlineItem.job_id, OutlineItem.chapter_index, OutlineItem.title, OutlineItem.type]
    name = "Outline Item"
    name_plural = "Outline Items"
    icon = "fa-solid fa-map-location-dot"
    category = "Planning"

class SDModelAdmin(ModelView, model=SdModel):
    column_list = [SdModel.name, SdModel.model_key, SdModel.is_default, SdModel.created_at]
    column_searchable_list = [SdModel.name, SdModel.model_key]
    name = "SD Model"
    name_plural = "SD Models"
    icon = "fa-solid fa-cube"
    category = "Assets"

class ImagePoolAdmin(ModelView, model=ImagePool):
    column_list = [ImagePool.image_tags, ImagePool.source_job_id, ImagePool.created_at]
    name = "Pool Image"
    name_plural = "Image Pool"
    icon = "fa-solid fa-images"
    category = "Assets"

def setup_admin(app: FastAPI):
    """Initialize SQLAdmin with models."""
    admin = Admin(app, engine, title="LuminaCast Dashboard")
    admin.add_view(JobAdmin)
    admin.add_view(SceneAdmin)
    admin.add_view(OutlineAdmin)
    admin.add_view(SDModelAdmin)
    admin.add_view(ImagePoolAdmin)
    return admin
