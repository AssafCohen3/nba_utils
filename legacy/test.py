import requests
url_address = "http://stats.nba.com/stats/leaguedashplayerbiostats/?perMode=PerGame&leagueId=00&season=2015-16&seasonType=Regular+Season&poRound=0&outcome=&location=&month=0&seasonSegment=&dateFrom=&dateTo=&opponentTeamId=0&vsConference=&vsDivision=&conference=&division=&gameSegment=&period=0&shotClockRange=&lastNGames=0&playerExperience=&playerPosition=&starterBench=&draftYear=&draftPick=&college=&country=&height=&weight="
url_address2 = "http://stats.nba.com/stats/commonplayerinfo/?playerId=201935&leagueId=00"
STATS_HEADERS = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Connection': 'keep-alive',
        'Referer': 'https://stats.nba.com/',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'}
# resp = requests.get(url_address2, headers=STATS_HEADERS)
# print(resp.text)
# data = resp.json()
# print(resp.json())


def aaaa():
    for i in range(0, 100):
        url = f'https://stats.nba.com/stats/playbyplayv{i}?GameId=0029600002&StartPeriod=0&EndPeriod=14'
        try:
            print(f'trying {url}')
            resp = requests.get(url, headers=STATS_HEADERS, timeout=10)
            datatext = resp.text
            data = resp.json()
            a = 3
        except:
            continue

if __name__ == '__main__':
    aaaa()