import datetime
import pprint
import sqlite3
import string
from collections import defaultdict
from collections.abc import Mapping
from constants import BREF_ABBREVATION_TO_NBA_TEAM_ID, DATABASE_PATH, DATABASE_NAME
from transactions.TransactionsParser import generate_transactions
from transactions.transaction_constants import ROLES, ABA_ABBR, TEAMS_MAPPING, TEAMS_IN_SEASONS_MAPPING


class TransactionAnalyzer:
    def __init__(self):
        self.tradees_analyzer = {
            'player': self.get_player_by_id,
            'player_no_id': self.get_player_by_name,
            'person_with_role': {
                'person': self.get_person_by_id,
                'person_no_id': self.get_person_by_name,
                'role': self.analyze_role
            },
            'cash': {
                'cash': lambda s, v: v,
                'cash_sum': self.analyze_cash,
                'cash_sum_pre': self.analyze_cash
            },
            'future_considerations': lambda s, v: 'future considerations',
            'cash_considerations': {
                'cash_considerations': lambda s, v: 'cash considerations',
                'cash_num': self.analyze_cash
            },
            'draft_pick': {
                'pick_year': lambda s, v: v if v == 'future' else int(v),
                'pick_round': lambda s, v: int(v[:1]),
                'player': self.get_player_by_id,
                'player_no_id': self.get_player_by_name
            },
            'trade_exception': {
                'trade_exception': lambda s, v: 'trade exception',
                'cash_num': self.analyze_cash
            }
        }
        self.executive_default = {
            'team': self.get_team_id_from_abbrevation,
            'person': self.get_person_by_id,
            'person_no_id': self.get_person_by_name,
            'role': self.analyze_role
        }
        self.movement_default = {
            'old_team': self.get_team_id_from_abbrevation,
            'new_team': self.get_team_id_from_abbrevation,
            'player': self.get_player_by_id,
            'player_no_id': self.get_player_by_name
        }
        self.player_team_default = {
            'player': self.get_player_by_id,
            'player_no_id': self.get_player_by_name,
            'team': self.get_team_id_from_abbrevation
        }
        self.analyzer = {
            'free_agent_sign': {
                **self.player_team_default,
                'additional': self.analyze_sign_additional
            },
            'sign': {
                **self.player_team_default,
                'additional': self.analyze_sign_additional
            },
            'multi_year_contract_sign': {
                **self.player_team_default,
                'additional': self.analyze_sign_additional
            },
            'convert_contract': {
                **self.player_team_default,
            },
            'sold_rights': {
                **self.movement_default,
                'additional': self.analyze_sold_rights_additional
            },
            'dispersal_draft': {
                **self.movement_default,
                'additional': self.analyze_sign_additional
            },
            'hiring': {
                **self.executive_default
            },
            'simple_trade': {
                'team_a': self.get_team_id_from_abbrevation,
                'team_a_tradees': self.tradees_analyzer,
                'team_b': self.get_team_id_from_abbrevation,
                'team_b_tradees': self.tradees_analyzer,
                'additional': self.analyze_trade_additional
            },
            'multiple_teams_trade': {
                'trades': {
                    'trading_team': self.get_team_id_from_abbrevation,
                    'tradees': self.tradees_analyzer,
                    'receiving_team': self.get_team_id_from_abbrevation
                },
                'additional': self.analyze_trade_additional
            },
            'penalty_trade': {
                'trading_team': self.get_team_id_from_abbrevation,
                'tradees': self.tradees_analyzer,
                'receiving_team': self.get_team_id_from_abbrevation,
                'penalized_team': self.get_team_id_from_abbrevation,
                'reason': self.analyze_penalty_reason
            },
            'one_side_trade': {
                'trading_team': self.get_team_id_from_abbrevation,
                'tradees': self.tradees_analyzer,
                'receiving_team': self.get_team_id_from_abbrevation,
                'additional': self.analyze_trade_additional
            },
            'waived': {
                **self.player_team_default,
                'reason': lambda s, v: v
            },
            'released': {
                **self.player_team_default,
            },
            'resignation': {
                **self.executive_default
            },
            'firing': {
                **self.executive_default
            },
            'appointment': {
                **self.executive_default,
                'role_more': lambda s, v: v
            },
            'reassignment': {
                **self.executive_default
            },
            'claimed_from_waivers': {
                **self.movement_default,
            },
            'expansion_draft': {
                **self.movement_default,
            },
            'retire_from_team': {
                **self.player_team_default,
            },
            'role_retire_from_team': {
                **self.executive_default
            },
            'sign_and_compensate': {
                **self.movement_default,
                'team_a_tradees': self.tradees_analyzer,
                'additional': self.analyze_sign_additional,
                'person_with_role': {
                    'person_no_id': self.get_person_by_name,
                    'role': self.analyze_role
                }
            },
            '10_day_contract': {
                **self.player_team_default,
            },
            'exhibit_10': {
                **self.player_team_default,
            },
            '10_day_contract_expired': {
                **self.player_team_default,
            },
            'release_from_10_day_contract': {
                **self.player_team_default,
            },
            'contract_extension': {
                **self.player_team_default,
            },
            'ceremonial_contract': {
                **self.player_team_default,
            },
            'subtitution_contract': {
                **self.player_team_default,
                'substituted_player_no_id': self.get_player_by_name
            },
            'two_way_contract_sign': {
                **self.player_team_default,
            },
            're_signing': {
                **self.player_team_default,
            },
            'rest_of_season_sign': {
                **self.player_team_default,
            },
            'sign_with_length': {
                **self.player_team_default,
                'contract_length': lambda s, v: int(v)
            },
            'suspension_by_team': {
                **self.player_team_default,
                'suspension_length': lambda s, v: int(v)
            },
            'suspension_by_league': {
                'player': self.get_player_by_id,
                'player_no_id': self.get_player_by_name,
                'suspension_length_games': lambda s, v: {'games': int(v)},
                'suspension_length_weeks': lambda s, v: {'weeks': int(v)},
            },
            'assigned_to': {
                **self.player_team_default,
                'assigned_to_team': lambda s, v: v,
                'where': lambda s, v: v if v == 'G-League' else None
            },
            'recalling': {
                **self.player_team_default,
                'assigned_to_team': lambda s, v: v,
                'where': lambda s, v: v if v == 'G-League' else None
            },
            'retirement': {
                'player': self.get_player_by_id,
                'retirement_season': lambda s, v: int(v.split('-')[0]),
                'retirement_date': lambda s, v: datetime.date(int('20' + v['year']), int(v['month']), int(v['day'])).isoformat(),
                'retirement_team': self.get_team_id_from_abbrevation
            }
        }
        self.bref_players = None
        self.bref_players_list = None
        self.conn = sqlite3.connect(DATABASE_PATH + DATABASE_NAME + '.sqlite')
        self.warnings = defaultdict(list)

    def load_players(self):
        all_players = self.conn.execute("""select PlayerId, PlayerName, FromYear, ToYear from BREFPlayer""").fetchall()
        self.bref_players = {}
        self.bref_players_list = all_players
        for p_id, p_name, p_from, p_to in all_players:
            self.bref_players[p_id] = [p_name, p_from, p_to]

    def get_bref_player_id(self, player_id):
        if self.bref_players is None:
            self.load_players()
        if player_id not in self.bref_players:
            self.warnings['not_found_id'].append(f'not found player id of {player_id}.')
            return {
                'player_id_not_found': player_id
            }
        return {
            'player_id': player_id,
            'player_name': self.bref_players[player_id][0],
            'from': self.bref_players[player_id][1],
            'to': self.bref_players[player_id][2],
        }

    def get_bref_player_name(self, season, player_name):
        if self.bref_players is None:
            self.load_players()
        relevants = [p for p in self.bref_players_list if p[1] == player_name and p[2] - 5 <= season <= p[3] + 5]
        if len(relevants) > 1:
            raise Exception('fffffff')
        if len(relevants) == 0:
            if len(player_name) > 20 or any(ext in player_name for ext in string.digits + string.punctuation):
                self.warnings['odd_name'].append(f'odd name {player_name}')
            else:
                self.warnings['not_found_name'].append(f'not found player {player_name} in {season}.')
            return {
                'player_name_not_found': player_name
            }
        self.warnings['success'].append(f'found {player_name} as {relevants[0]}')
        return {
            'player_id': relevants[0][0],
            'player_name': relevants[0][1],
            'from': relevants[0][2],
            'to': relevants[0][3],
        }

    @staticmethod
    def get_team_id_from_abbrevation(season, abbr):
        if abbr not in BREF_ABBREVATION_TO_NBA_TEAM_ID:
            if abbr in ABA_ABBR:
                return {
                    'team_name_aba': abbr + '(ABA)',
                    'abbr': abbr
                }
            if abbr in TEAMS_MAPPING:
                return {
                    'team_id': TEAMS_MAPPING[abbr],
                    'abbr': abbr
                }
            print(f'not found team {abbr}')
            return None
        relevant = set([t[2] for t in BREF_ABBREVATION_TO_NBA_TEAM_ID[abbr] if t[0] - 3 <= season <= t[1] + 3])
        if len(relevant) > 1:
            raise Exception('tfff')
        if len(relevant) == 0:
            if (season, abbr) in TEAMS_IN_SEASONS_MAPPING:
                return {
                    'team_id': TEAMS_IN_SEASONS_MAPPING[(season, abbr)],
                    'abbr': abbr
                }
        return {
            'team_id': list(relevant)[0],
            'abbr': abbr
        }

    def analyze_tradees(self, season, tradees):
        to_ret = defaultdict(list)
        for key, values in tradees.items():
            for value in values:
                v = self.tradees_analyzer[key](season, value)
                if v is None:
                    raise Exception('whattt')
                to_ret[key].append(v)
        return dict(to_ret)

    @staticmethod
    def analyze_role(_, role):
        return role if ROLES.index(role) >= 0 else None

    @staticmethod
    def analyze_trade_additional(_, additional):
        return additional

    @staticmethod
    def analyze_sign_additional(_, additional):
        return additional

    @staticmethod
    def analyze_sold_rights_additional(_, additional):
        return additional

    @staticmethod
    def analyze_penalty_reason(_, reason):
        return reason

    @staticmethod
    def get_person_by_id(_, person_id):
        return {
            'person_not_analyzed': person_id
        }

    @staticmethod
    def get_person_by_name(_, person_name):
        return person_name

    @staticmethod
    def analyze_cash(_, cash):
        if cash.endswith('MM'):
            return float(cash[1:-2]) * 1000000
        elif cash.endswith('M'):
            return float(cash[1:-1]) * 1000000
        elif cash.endswith('K'):
            return float(cash[1:-1]) * 1000
        return float(cash[1:])

    def get_player_by_name(self, season, player_name):
        return self.get_bref_player_name(season, player_name)

    def get_player_by_id(self, _, player_id):
        return self.get_bref_player_id(player_id)

    def get_value_in_path(self, obj, path, depth=0):
        try:
            res = self.get_value_in_path(obj[path[0]], path[1:], depth+1) if len(path) > 1 else obj[path[0]]
            return res
        except Exception as e:
            if depth == 0:
                print(f'failed getting {path}')
            raise e

    def analyze_value(self, season, value, path):
        handler = self.get_value_in_path(self.analyzer, path)
        returned_val = handler(value, season)
        print(f'analyzed {value} in path {path} in {season} as {returned_val}')
        return returned_val

    def analyze_transaction(self, season, full, transaction, cur_analyzer, path, depth):
        to_ret = defaultdict(list)
        for key, value in transaction.items():
            handler = cur_analyzer[key]
            if isinstance(handler, Mapping):
                to_iterate = []
                if isinstance(value, list):
                    to_iterate.extend(value)
                else:
                    to_iterate.append(value)
                for v in to_iterate:
                    new_val = self.analyze_transaction(season, full, v, cur_analyzer[key], path + [key], depth + 1)
                    to_ret[key].append(new_val)
            else:
                to_iterate = []
                if isinstance(value, list):
                    to_iterate.extend(value)
                else:
                    to_iterate.append(value)
                for v in to_iterate:
                    val = handler(season, v)
                    if val is None:
                        raise Exception('what')
                    # print(f'{"--"*depth} {path + [key]} analyzed {v} as {val}')
                    to_ret[key].append(val)
        return dict(to_ret)

    @staticmethod
    def validate_analyzed(analyzed, transaction_to_find):
        found_elements = set()

        def check_element(key, value):
            if key in ('player_id_not_found', 'player_id'):
                found_elements.add((value, 'player'))
            elif key in ('abbr',):
                found_elements.add((value, 'team'))
            elif key in ('person_not_analyzed',):
                found_elements.add((value, 'executive'))

        def collect_elements(analyzed_transaction):
            for key, value in analyzed_transaction.items():
                if isinstance(value, list):
                    for v in value:
                        if isinstance(v, Mapping):
                            collect_elements(v)
                        else:
                            check_element(key, v)
                else:
                    check_element(key, value)

        collect_elements(analyzed)
        for id_to_found, (id_type, id_text) in transaction_to_find.items():
            if id_type == 'coach':
                id_type = 'executive'
            if (id_to_found, id_type) not in found_elements:
                raise Exception(f'couldnt validate {id_to_found}, of type {id_type} in {analyzed}. found {found_elements}')

    def analyze_transactions(self):
        for season, transaction, transaction_type, parsed_transaction, transaction_to_find in generate_transactions():
            try:
                print(f'analyzing {transaction} in season {season}')
                print(f'parsed as {parsed_transaction} of type {transaction_type}')
                res = self.analyze_transaction(season, parsed_transaction, parsed_transaction, self.analyzer[transaction_type], [], 1)
                print('analyzed as: ')
                pprint.pprint(res)
                print('validating...')
                if 'The TRI hired pottero99c as Head Coach.' in transaction:
                    a = 0
                self.validate_analyzed(res, transaction_to_find)
            except Exception as e:
                self.print_warnings()
                print(f'analyzing {transaction} in season {season}')
                print(f'parsed as {parsed_transaction} of type {transaction_type}')
                raise e
        self.print_warnings()

    def print_warnings(self):
        for key, items in self.warnings.items():
            print(f'{key}: ')
            for item in items:
                print(f'    {item}')


if __name__ == '__main__':
    analyzer = TransactionAnalyzer()
    analyzer.analyze_transactions()