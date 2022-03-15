import pbpstats

pbpstats.REQUEST_TIMEOUT = 60
from pbpstats.resources.enhanced_pbp import (
    FieldGoal,
    Foul,
    FreeThrow,
    JumpBall,
    Substitution,
    Rebound,
    Timeout,
    Turnover,
)
from pbpstats.resources.enhanced_pbp.stats_nba.rebound import StatsRebound
import pbpstats.resources.enhanced_pbp.stats_nba.enhanced_pbp_item as pbpItemClass
from pbpstats.resources.enhanced_pbp.stats_nba.enhanced_pbp_item import StatsEnhancedPbpItem


class Object(object):
    pass


pbpItemClass.KEY_ATTR_MAPPER['WCTIMESTRING'] = 'real_time'
pbpItemClass.KEY_ATTR_MAPPER['PERSON1TYPE'] = 'person1_type'
pbpItemClass.KEY_ATTR_MAPPER['PERSON2TYPE'] = 'person2_type'
pbpItemClass.KEY_ATTR_MAPPER['PLAYER2_TEAM_ID'] = 'player2_team_id'
pbpItemClass.KEY_ATTR_MAPPER['PERSON3TYPE'] = 'person3_type'
pbpItemClass.KEY_ATTR_MAPPER['PLAYER3_TEAM_ID'] = 'player3_team_id'
pbpItemClass.KEY_ATTR_MAPPER['SCOREMARGIN'] = 'score_margin_text'

def get_offense_team_id(self):
    """
    returns team id for team on offense for event
    """
    if isinstance(self, Foul) and (self.is_charge or self.is_offensive_foul):
        # offensive foul returns team id
        # this isn't separate method in Foul class because some fouls can be committed
        # on offense or defense (loose ball, flagrant, technical)
        return self.team_id
    event_to_check = self.previous_event
    team_ids = list(self.current_players.keys())
    while event_to_check is not None and not (
            isinstance(event_to_check, (FieldGoal, JumpBall))
            or (
                    isinstance(event_to_check, Turnover)
                    and not event_to_check.is_no_turnover
            )
            or (isinstance(event_to_check, Rebound) and event_to_check.is_real_rebound)
            or (
                    isinstance(event_to_check, FreeThrow)
                    and not event_to_check.is_technical_ft
            )
    ):
        event_to_check = event_to_check.previous_event
    if event_to_check is None and self.next_event is not None \
            and (not isinstance(self.next_event, Turnover) or not self.next_event.is_no_turnover or self.next_event.previous_event != self):
        # should only get here on first possession of period when first event is non-offensive foul,
        # FieldGoal, FreeThrow, Rebound, Turnover, JumpBall
        return self.next_event.get_offense_team_id()
    if isinstance(event_to_check, Turnover) and not event_to_check.is_no_turnover:
        return (
            team_ids[0]
            if team_ids[1] == event_to_check.get_offense_team_id()
            else team_ids[1]
        )
    if isinstance(event_to_check, Rebound) and event_to_check.is_real_rebound:
        if not event_to_check.oreb:
            return (
                team_ids[0]
                if team_ids[1] == event_to_check.get_offense_team_id()
                else team_ids[1]
            )
        return event_to_check.get_offense_team_id()
    if isinstance(event_to_check, (FieldGoal, FreeThrow)):
        if event_to_check.is_possession_ending_event:
            return (
                team_ids[0]
                if team_ids[1] == event_to_check.get_offense_team_id()
                else team_ids[1]
            )
        return event_to_check.get_offense_team_id()
    if isinstance(event_to_check, JumpBall):
        if event_to_check.count_as_possession:
            team_ids = list(self.current_players.keys())
            return (
                team_ids[0]
                if team_ids[1] == event_to_check.get_offense_team_id()
                else team_ids[1]
            )
        return event_to_check.get_offense_team_id()

@property
def new_rebound_missed_shot_property(self):
    """
    returns :obj:`~pbpstats.resources.enhanced_pbp.field_goal.FieldGoal` or
    :obj:`~pbpstats.resources.enhanced_pbp.free_throw.FreeThrow` object
    for shot that was missed

    :raises: :obj:`~pbpstats.resources.enhanced_pbp.rebound.EventOrderError`:
        If rebound event is not immediately following a missed shot event.
    """
    if isinstance(self.previous_event, (FieldGoal, FreeThrow)):
        if not self.previous_event.is_made:
            return self.previous_event
    elif (
        isinstance(self.previous_event, Turnover)
        and self.previous_event.is_shot_clock_violation
    ):
        if isinstance(self.previous_event, FieldGoal):
            return self.previous_event.previous_event
    elif isinstance(self.previous_event, JumpBall):
        prev_event = self.previous_event.previous_event
        while isinstance(prev_event, (Substitution, Timeout)):
            prev_event = prev_event.previous_event
        if isinstance(prev_event, (FieldGoal, FreeThrow)):
            return prev_event
    to_ret = Object()
    setattr(to_ret, 'seconds_remaining', 20)
    setattr(to_ret, 'team_id', None)
    return to_ret


setattr(StatsRebound, 'missed_shot', new_rebound_missed_shot_property)
setattr(StatsEnhancedPbpItem, 'get_offense_team_id', get_offense_team_id)