"""
Grabbite — Blog model.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# BLOG
# ─────────────────────────────────────────────────────────────────────────────
class Blog(db.Model):
    __tablename__ = 'blogs'

    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    slug       = db.Column(db.String(220), unique=True)
    content    = db.Column(db.Text, nullable=False)
    author     = db.Column(db.String(100), nullable=False, default='Grabbite Team')
    image      = db.Column(db.String(255), default='blog_default.jpg')
    excerpt    = db.Column(db.Text)
    category   = db.Column(db.String(50), default='Food')
    status     = db.Column(db.String(20), default='published', index=True)  # LOW-13 / PERF-8: index for filter_by(status=...)
    featured   = db.Column(db.Boolean, default=False)
    views      = db.Column(db.Integer, default=0)
    tags       = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        title: str = '',
        content: str = '',
        author: str = 'Grabbite Team',
        image: str = 'blog_default.jpg',
        excerpt: Optional[str] = None,
        category: str = 'Food',
        status: str = 'published',
        featured: bool = False,
        tags: Optional[str] = None,
        slug: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.content = content
        self.author = author
        self.image = image
        self.excerpt = excerpt
        self.category = category
        self.status = status
        self.featured = featured
        self.tags = tags
        self.slug = slug

    def generate_slug(self):
        """Auto-generate URL slug from title.

        LOW-8: Handles duplicate slugs — if the candidate slug already exists
        in the DB, a short random suffix is appended until the slug is unique.
        """
        import re, secrets as _sec
        base = self.title.lower()
        base = re.sub(r'[^a-z0-9\s-]', '', base)
        base = re.sub(r'\s+', '-', base.strip())
        base = base[:200]  # leave room for suffix

        candidate = base
        max_attempts = 5
        for attempt in range(max_attempts):
            # Check for conflict, but exclude self (for edit operations)
            conflict_query = Blog.query.filter(Blog.slug == candidate)
            if self.id:
                conflict_query = conflict_query.filter(Blog.id != self.id)
            if not conflict_query.first():
                self.slug = candidate
                return candidate
            suffix = _sec.token_hex(2)          # 4 hex chars — short but unique enough
            candidate = f'{base}-{suffix}'

        # Fallback: full hex to guarantee no collision
        self.slug = f'{base}-{_sec.token_hex(4)}'
        return self.slug

    def __repr__(self):
        return f'<Blog "{self.title[:40]}">'
