from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from zoneinfo import ZoneInfo

engine = create_engine("sqlite:///database.db")
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Group(Base):
    __tablename__ = "groups"

    id = Column(BigInteger, primary_key=True)
    title = Column(String(255), nullable=False)
    total_swears = Column(Integer, nullable=False, default=0)
    total_points = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(ZoneInfo("Asia/Tehran")),
    )

    users = relationship("User", back_populates="group")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False)
    first_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    swear_count = Column(Integer, nullable=False, default=0)
    points = Column(Integer, nullable=False, default=0)

    group = relationship("Group", back_populates="users")

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="unique_user_per_group"),
    )


def create_tables():
    Base.metadata.create_all(engine)


def create_group(group_id: int, title: str):
    with Session() as session:
        exists = session.query(Group).filter(Group.id == group_id).first()
        if exists:
            return

        group = Group(id=group_id, title=title)
        session.add(group)
        session.commit()


def create_user(user_id: int, group_id: int, first_name: str, username: str | None = None):
    with Session() as session:
        exists = (
            session.query(User)
            .filter(User.user_id == user_id, User.group_id == group_id)
            .first()
        )
        if exists:
            return

        user = User(
            user_id=user_id,
            group_id=group_id,
            first_name=first_name,
            username=username,
        )
        session.add(user)
        session.commit()


def get_user(user_id: int, group_id: int):
    with Session() as session:
        return (
            session.query(User)
            .filter(User.user_id == user_id, User.group_id == group_id)
            .first()
        )


def get_group(group_id: int):
    with Session() as session:
        return session.query(Group).filter(Group.id == group_id).first()


def increase_swears_and_points(user_id: int, group_id: int, points: int):
    with Session() as session:
        user = (
            session.query(User)
            .filter(User.user_id == user_id, User.group_id == group_id)
            .first()
        )
        group = session.query(Group).filter(Group.id == group_id).first()

        if user and group:
            user.swear_count += 1
            user.points += points

            group.total_swears += 1
            group.total_points += points

            session.commit()


def get_all_users():
    with Session() as session:
        return session.query(User).all()


def get_all_groups():
    with Session() as session:
        return session.query(Group).all()


def get_user_stats(user_id, group_id):
    with Session() as session:
        user = session.query(User).filter(User.user_id == user_id, User.group_id == group_id).first()
        if not user:
            return None

        higher = session.query(User).filter(User.group_id == group_id, User.points > user.points).count()
        rank = higher + 1 

        total = session.query(User).filter(User.group_id == group_id).count()

        return {
            "points": user.points,
            "swear_count": user.swear_count,
            "rank": rank,
            "total": total,
        }


def get_top_users(group_id: int, limit: int = 10):
    with Session() as session:
        return (
            session.query(User)
            .filter(User.group_id == group_id)
            .order_by(User.points.desc())
            .limit(limit)
            .all()
        )


def get_all_groups():
    with Session() as session:
        groups = session.query(Group).order_by(Group.total_points.desc()).all()
        return groups

