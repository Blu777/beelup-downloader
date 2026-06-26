from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class AuthConfig:
    google_enabled: bool = False
    google_client_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthConfig":
        if not data:
            return cls()
        return cls(
            google_enabled=data.get("google_enabled", False),
            google_client_id=data.get("google_client_id")
        )

@dataclass
class MediaConfig:
    cutout_enabled: bool = False
    card_download_enabled: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaConfig":
        if not data:
            return cls()
        return cls(
            cutout_enabled=data.get("cutout_enabled", False),
            card_download_enabled=data.get("card_download_enabled", False)
        )

@dataclass
class SignupWindow:
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    is_open: bool = False
    message: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignupWindow":
        if not data:
            return cls()
        return cls(
            opens_at=data.get("opens_at"),
            closes_at=data.get("closes_at"),
            is_open=data.get("is_open", False),
            message=data.get("message", "")
        )

@dataclass
class PlayerStats:
    pace: int = 50
    shooting: int = 50
    passing: int = 50
    dribbling: int = 50
    defense: int = 50
    physical: int = 50

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerStats":
        if not data:
            return cls()
        return cls(
            pace=data.get("pace", 50),
            shooting=data.get("shooting", 50),
            passing=data.get("passing", 50),
            dribbling=data.get("dribbling", 50),
            defense=data.get("defense", 50),
            physical=data.get("physical", 50)
        )

    def to_dict(self) -> Dict[str, int]:
        return {
            "pace": self.pace,
            "shooting": self.shooting,
            "passing": self.passing,
            "dribbling": self.dribbling,
            "defense": self.defense,
            "physical": self.physical
        }

@dataclass
class Player:
    id: str
    display_name: str
    email: Optional[str] = None
    position: Optional[str] = None
    positions: List[str] = field(default_factory=list)
    primary_position: Optional[str] = None
    position_label: str = ""
    position_text: str = ""
    smokes: bool = False
    photo_url: str = ""
    is_admin: bool = False
    is_self: bool = False
    is_guest: bool = False
    guest_skill_level: Optional[str] = None
    guest_skill_label: Optional[str] = None
    can_vote: bool = False
    stats: PlayerStats = field(default_factory=PlayerStats)
    user_vote: Optional[Dict[str, int]] = None
    overall: int = 70
    votes_count: int = 0
    wins: int = 0
    matches_played: int = 0
    win_rate: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        return cls(
            id=data.get("id", ""),
            display_name=data.get("display_name", "Desconocido"),
            email=data.get("email"),
            position=data.get("position"),
            positions=data.get("positions", []),
            primary_position=data.get("primary_position"),
            position_label=data.get("position_label", ""),
            position_text=data.get("position_text", ""),
            smokes=data.get("smokes", False),
            photo_url=data.get("photo_url", ""),
            is_admin=data.get("is_admin", False),
            is_self=data.get("is_self", False),
            is_guest=data.get("is_guest", False),
            guest_skill_level=data.get("guest_skill_level"),
            guest_skill_label=data.get("guest_skill_label"),
            can_vote=data.get("can_vote", False),
            stats=PlayerStats.from_dict(data.get("stats", {})),
            user_vote=data.get("user_vote"),
            overall=data.get("overall", 70),
            votes_count=data.get("votes_count", 0),
            wins=data.get("wins", 0),
            matches_played=data.get("matches_played", 0),
            win_rate=data.get("win_rate", 0.0)
        )

@dataclass
class SignupEntry:
    id: str
    display_name: str
    email: Optional[str] = None
    position: Optional[str] = None
    position_label: str = ""
    is_guest: bool = False
    guest_skill_label: Optional[str] = None

    @classmethod
    def from_dict_or_str(cls, item: Any) -> "SignupEntry":
        if isinstance(item, str):
            return cls(id=item, display_name=item)
        if isinstance(item, dict):
            return cls(
                id=item.get("id", ""),
                display_name=item.get("display_name", ""),
                email=item.get("email"),
                position=item.get("position"),
                position_label=item.get("position_label", ""),
                is_guest=item.get("is_guest", False),
                guest_skill_label=item.get("guest_skill_label")
            )
        return cls(id=str(item), display_name=str(item))

@dataclass
class NextMatch:
    id: str
    scheduled_at: str
    date_label: str
    time_label: str
    max_signups: int
    signup_window: SignupWindow
    teams_ready: bool = False
    teams: Dict[str, List[Player]] = field(default_factory=lambda: {"A": [], "B": []})
    signups: List[SignupEntry] = field(default_factory=list)
    signed_count: int = 0
    guest_count: int = 0
    is_user_signed: bool = False
    can_sign: bool = False
    reason: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NextMatch":
        teams_data = data.get("teams", {})
        parsed_teams = {
            "A": [Player.from_dict(p) for p in teams_data.get("A", [])],
            "B": [Player.from_dict(p) for p in teams_data.get("B", [])]
        }
        raw_signups = data.get("signups", [])
        parsed_signups = [SignupEntry.from_dict_or_str(s) for s in raw_signups]
        
        return cls(
            id=data.get("id", ""),
            scheduled_at=data.get("scheduled_at", ""),
            date_label=data.get("date_label", ""),
            time_label=data.get("time_label", ""),
            max_signups=data.get("max_signups", 16),
            signup_window=SignupWindow.from_dict(data.get("signup_window", {})),
            teams_ready=data.get("teams_ready", False),
            teams=parsed_teams,
            signups=parsed_signups,
            signed_count=data.get("signed_count", data.get("signups_count", len(parsed_signups))),
            guest_count=data.get("guest_count", 0),
            is_user_signed=data.get("is_user_signed", False),
            can_sign=data.get("can_sign", False),
            reason=data.get("reason", "")
        )

@dataclass
class MatchHistory:
    id: str
    scheduled_at: str
    label: str
    status: str
    signup_window: SignupWindow
    signups: List[Player] = field(default_factory=list)
    signups_count: int = 0
    teams_ready: bool = False
    teams: Dict[str, List[Player]] = field(default_factory=lambda: {"A": [], "B": []})
    winner: Optional[str] = None
    score_label: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchHistory":
        teams_data = data.get("teams", {})
        parsed_teams = {
            "A": [Player.from_dict(p) for p in teams_data.get("A", [])],
            "B": [Player.from_dict(p) for p in teams_data.get("B", [])]
        }
        return cls(
            id=data.get("id", ""),
            scheduled_at=data.get("scheduled_at", ""),
            label=data.get("label", ""),
            status=data.get("status", ""),
            signup_window=SignupWindow.from_dict(data.get("signup_window", {})),
            signups=[Player.from_dict(p) for p in data.get("signups", []) if isinstance(p, dict)],
            signups_count=data.get("signups_count", 0),
            teams_ready=data.get("teams_ready", False),
            teams=parsed_teams,
            winner=data.get("winner"),
            score_label=data.get("score_label"),
            notes=data.get("notes")
        )

@dataclass
class GeneralStats:
    editions: int
    porros_smoked: float
    grams_smoked: float
    motality_rate: float

@dataclass
class Guest:
    id: str
    display_name: str
    skill_level: str

@dataclass
class MvpCandidate:
    id: str
    display_name: str
    team: str
    position_label: str
    photo_url: str

@dataclass
class BootstrapData:
    now: str
    auth: AuthConfig
    media: MediaConfig
    session_user: Optional[Dict[str, Any]]
    next_match: NextMatch
    players: List[Player]
    matches: List[MatchHistory]
    latest_mvp: Optional[Dict[str, Any]] = None
    pending_mvp_vote: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BootstrapData":
        return cls(
            now=data.get("now", ""),
            auth=AuthConfig.from_dict(data.get("auth", {})),
            media=MediaConfig.from_dict(data.get("media", {})),
            session_user=data.get("session_user"),
            next_match=NextMatch.from_dict(data.get("next_match", {})),
            players=[Player.from_dict(p) for p in data.get("players", [])],
            matches=[MatchHistory.from_dict(m) for m in data.get("matches", [])],
            latest_mvp=data.get("latest_mvp"),
            pending_mvp_vote=data.get("pending_mvp_vote")
        )
