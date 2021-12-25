from flask import render_template
import pandas as pd
import requests

#ikke i bruk enda
def winners():
    def getWinners():
        url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        events = requests.get(url).json()['events']
        nyRunde = [(1, 8), (9, 16), (17, 24), (25, 32), (33, 38)]
        winnerList = []
        i = 0
        gwIntervall = ["1 → 8", "9 → 16", "17 → 24", "25 → 32", "33 → 38"]
        for rndS, rndE in nyRunde:
            if events[rndE - 1]['data_checked']:
                rundevinnere = getRoundWinners(rndS, rndE)
                winnerPage.append({
                    'GW': gwIntervall[i],
                    'Vinner': rundevinnere[1],
                    'Poeng': rundevinnere[0]
                })
                i += 1
        return winnerList
    data = getWinners()

    winnerPage = render_template('vinnere.html', data = data)

    return winnerPage

def getRoundWinners(roundStart, roundEnd):
    roundWinners = (any, any)
    high = 0
    teamsList = getTeamList()
    for i in range(len(teamsList)):
        url = 'https://fantasy.premierleague.com/api/entry/' + str(teamsList.at[i, 'entry']) + '/history/'
        teamPoints = requests.get(url).json()['current']
        if roundEnd == 8:
            if high < teamPoints[roundEnd - 1]['total_points']:
                roundWinners = (teamPoints[roundEnd - 1]['total_points'], teamsList.at[i, 'player_name'])
                high = teamPoints[roundEnd - 1]['total_points']
        else:
            if high < (teamPoints[roundEnd - 1]['total_points'] -
                        teamPoints[roundStart - 2]['total_points']):
                roundWinners = (
                    teamPoints[roundEnd - 1]['total_points'] -
                    teamPoints[roundStart - 2]['total_points'], teamsList.at[i, 'player_name'])
                high = teamPoints[roundEnd - 1]['total_points'] - teamPoints[roundStart - 2]['total_points']
    return roundWinners



def getTeamList():
    try:
        url2 = 'https://fantasy.premierleague.com/api/leagues-classic/448728/standings/'
        r2 = requests.get(url2)
        json2 = r2.json()
        standings_df = pd.DataFrame(json2['standings'])
        league_df = pd.DataFrame(standings_df['results'].values.tolist())
        return league_df[['entry', 'player_name']]
    except:
        return None