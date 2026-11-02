from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator

class ResumeRequest(BaseModel):
    resume_text: str = Field(..., description="Raw resume text pasted by the user")

    @field_validator("resume_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 20:
            raise ValueError("resume_text is too short to be a resume (min 20 characters)")
        return v

class Project(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("project name cannot be empty")
        return v

class ResumeData(BaseModel):
    """Structured output. `None` means 'not stated in the resume' - never a guess."""

    name: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    # Professional (paid) experience only. Internships and personal/academic
    # projects are NOT counted here.
    years_of_experience: Optional[Union[int, float]] = Field(default=None, ge=0, le=60)
    projects: list[Project] = Field(default_factory=list)
    # Kept separate so internships never inflate years_of_experience.
    internships: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = " ".join(v.split())
        return v or None

    @field_validator("years_of_experience")
    @classmethod
    def whole_numbers_as_int(cls, v):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v