from sqlalchemy import Column, PrimaryKeyConstraint
from sqlalchemy import Integer, Text, Date, Float
from base import Base


class BoxScoreT(Base):
    __tablename__ = 'BoxScoreT'
    Season = Column(Integer)
    SeasonType = Column(Text)
    TeamId = Column(Integer)
    TeamAbbreviation = Column(Text)
    TeamName = Column(Text)
    TeamAId = Column(Integer)
    TeamAName = Column(Text)
    TeamBId = Column(Integer)
    TeamBName = Column(Text)
    GameId = Column(Text)
    GameDate = Column(Date)
    Matchup = Column(Text)
    IsHome = Column(Integer)
    WL = Column(Text)
    MIN = Column(Integer)
    FGM = Column(Integer)
    FGA = Column(Integer)
    FG_PCT = Column(Float)
    FG3M = Column(Integer)
    FG3A = Column(Integer)
    FG3_PCT = Column(Float)
    FTM = Column(Integer)
    FTA = Column(Integer)
    FT_PCT = Column(Float)
    OREB = Column(Integer)
    DREB = Column(Integer)
    REB = Column(Integer)
    AST = Column(Integer)
    STL = Column(Integer)
    BLK = Column(Integer)
    TOV = Column(Integer)
    PF = Column(Integer)
    PTS = Column(Integer)
    PlusMinus = Column(Integer)
    VideoAvailable = Column(Integer)
    __table_args__ = (
        PrimaryKeyConstraint('GameId', 'TeamId'),
    )
