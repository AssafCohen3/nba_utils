import sqlite3
import os
import pandas as pd
import requests
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

import OddsCacheHandler
from OddsCacheHandler import OddsCacheHandler
from constants import *
from BoxScoreCacheHandler import BoxScoreCacheHandler


def create_data_frame(data, headers):
    return pd.DataFrame(data=data, columns=headers)


def handle_cache(cache_handler):
    file_name = cache_handler.get_filename()
    if os.path.isfile(file_name):
        print(f"found {file_name} in cache.")
        with open(file_name, "rb") as f:
            to_ret = cache_handler.load_file(f)
    else:
        with open(missing_files, "r+") as f:
            if file_name in [line.strip() for line in f.readlines()]:
                print(f"file {file_name} is missing. skipping.")
                raise ValueError()
        to_ret = cache_handler.downloader()
        print(f"Downloaded {file_name}.")
        if cache_handler.to_cache(to_ret):
            with open(file_name, "w") as f2:
                cache_handler.cache(to_ret, f2)
            print(f"Cached {file_name}.")
    return to_ret


def collect_all_boxscores(season_type_index, box_score_type):
    df = None
    date_from = ""
    continue_loop = True
    while continue_loop:
        data = handle_cache(BoxScoreCacheHandler(date_from, season_type_index, box_score_type))
        data = data["resultSets"][0]
        headers = data["headers"]
        results = data["rowSet"]
        print(f"found {len(results)} games in {SEASON_TYPES[season_type_index].replace('+', ' ')} of type {box_score_type} from date {date_from}")
        if len(results) >= API_COUNT_THRESHOLD:
            game_date_index = headers.index("GAME_DATE")
            count = 0
            last_date = results[-1][game_date_index]
            while results[-1][game_date_index] == last_date:
                results.pop()
                count = count+1
            print(f"popped last {count} items.")
            date_from = last_date
        else:
            continue_loop = False
        new_df = create_data_frame(results, headers)
        df = new_df if df is None else pd.concat([df, new_df], ignore_index=True)
    return df


def add_sorted_teams_matchups(df):
    matchup_re_str = r'(.*) (?:@|vs.) (.*)'
    a = df['MATCHUP'].str.extract(matchup_re_str)
    a = a.to_numpy()
    a.sort(axis=1)
    a = pd.DataFrame(data=a, columns=["team1", "team2"])
    df["MATCHUP_TEAM1"] = a["team1"]
    df["MATCHUP_TEAM2"] = a["team2"]


def create_boxscores_table(conn, box_score_type):
    all_boxscores_df = None
    for i in range(0, len(SEASON_TYPES)):
        new_df = collect_all_boxscores(i, box_score_type)
        all_boxscores_df = new_df if all_boxscores_df is None else pd.concat([all_boxscores_df, new_df], ignore_index=True)
    season_and_type = all_boxscores_df["SEASON_ID"].str.extract(r'(\d)(\d*)')
    all_boxscores_df["SEASON_TYPE"] = season_and_type[0]
    all_boxscores_df["SEASON"] = season_and_type[1]
    add_sorted_teams_matchups(all_boxscores_df)
    all_boxscores_df.to_sql(f'BoxScore{box_score_type}', conn, if_exists='replace', index=False)


def collect_season_odds(season):
    df = handle_cache(OddsCacheHandler(season))
    to_ret = None
    for j, odds_round in enumerate(ODDS_TYPES):
        round_df = df["Team"].join(df["Playoffs,prior to..."][odds_round]).dropna().rename(columns={odds_round: "odd"})
        round_df["ROUND"] = j
        round_df["SEASON"] = season
        to_ret = round_df if to_ret is None else pd.concat([to_ret, round_df], ignore_index=True)
    return to_ret


def collect_all_odds():
    df = None
    for i in range(1972, LAST_SEASON):
        try:
            new_df = collect_season_odds(i)
        except ValueError:
            print(f"not found season {i}.")
            continue
        df = new_df if df is None else pd.concat([df, new_df], ignore_index=True)
    return df


def create_odds_table(conn):
    df = collect_all_odds()
    df.to_sql("Odds", conn, if_exists='replace', index=False)


def get_connection():
    return sqlite3.connect(f"Database/{DATABASE_NAME}.sqlite")


def create_database():
    conn = get_connection()
    create_boxscores_table(conn, "P")
    create_boxscores_table(conn, "T")
    create_odds_table(conn)
    conn.commit()


def get_most_seasons_avg(conn, seasons_range, min_career, max_season):
    statement = """select (PC.FirstYear/ :range * :range) as season, round(avg(SeasonsAt), 2) as AverageMostSeasonsAtTeam
                    from PlayerTeamMostSeasons PTMS join PlayerCareer PC on PTMS.PLAYER_ID = PC.PLAYER_ID
                    where PC.CareerLength >= :min_career and season <= :max_season group by PC.FirstYear/:range * :range
"""
    cur = conn.cursor()
    cur.execute(statement, {"range": seasons_range, "min_career": min_career, "max_season": max_season})
    rows = cur.fetchall()
    return rows


def get_adjusted_teams_avg(conn, seasons_range, min_career, max_season):
    statement = """select (FirstYear / :range) * :range as SEASON, round(avg(AdjustedTeamNumber), 2) as AverageAdjustedTeamsNumber from PlayerAdjustedTeamsNumber
                    where SEASON <= :max_season and CareerLength >= :min_career
                    group by (FirstYear / :range) * :range
"""

    cur = conn.cursor()
    cur.execute(statement, {"range": seasons_range, "min_career": min_career, "max_season": max_season})
    rows = cur.fetchall()
    return rows


def get_teams_avg(conn, seasons_range, min_career, max_season):
    statement = """select (FirstYear / :range) * :range as SEASON, round(avg(PlayerTeamNumber), 2) as AverageAdjustedTeamsNumber from PlayerAdjustedTeamsNumber
                    where SEASON <= :max_season and CareerLength >= :min_career
                    group by (FirstYear / :range) * :range
"""

    cur = conn.cursor()
    cur.execute(statement, {"range": seasons_range, "min_career": min_career, "max_season": max_season})
    rows = cur.fetchall()
    return rows


def plot_average_most_seasons():
    conn = get_connection()
    res_rows = get_most_seasons_avg(conn, 5, 5, 2010)
    points = [(row[0], row[1]) for row in res_rows]
    print(points)
    plt.scatter(*zip(*points))
    plt.ylim(0, 10)
    plt.show()


def plot_average_player_teams_number():
    conn = get_connection()
    average_teams_number = get_teams_avg(conn, 5, 5, 2005)
    adjusted_average_teams_number = get_adjusted_teams_avg(conn, 5, 5, 2005)
    average_teams_points = [(row[0], row[1]) for row in average_teams_number]
    adjusted_average_teams_points = [(row[0], row[1]) for row in adjusted_average_teams_number]
    print(f"{average_teams_points=}")
    print(f"{adjusted_average_teams_points=}")
    plt.scatter(*zip(*average_teams_points), color='blue', label="regular average")
    plt.scatter(*zip(*adjusted_average_teams_points), color='red', label="adjusted average")
    plt.legend()
    plt.ylim(0, 10)
    plt.show()


def differ(list1, list2):
    differ_list = [x for x in list2 if x not in list1]
    print(differ_list)


def scrape_odds():
    url_address = "https://www.sportsoddshistory.com/nba-main/?y=1972-1973&sa=nba&a=finals&o=r"
    r = requests.get(url_address)
    df = None
    if r.status_code == 200:
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table', {"class": "soh1"})
        df = pd.read_html(str(table))[0]
        print(df)
        a = 0

def test():
    url_address = "https://stats.nba.com/stats/commonplayoffseries?LeagueID=00&Season=1946-47&SeriesID="
    res = requests.get(url_address, headers=STATS_HEADERS).json()
    data = res["resultSets"][0]
    results = data["rowSet"]
    a = 0

print("Boxscore DB: Select algorithm")
