from flask import render_template
import pandas as pd
import requests
from datetime import datetime
import time

def fixtures():
    def getTeamInfo():
        url4 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r4 = requests.get(url4)
        teams = r4.json()['teams']
        return teams

    def checkGameweek():
        url3 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r3 = requests.get(url3)
        json = r3.json()
        gameweek_df = pd.DataFrame(json['events'])
        iscurrent = gameweek_df[['id', 'is_current']]
        currentGw = iscurrent.loc[(iscurrent.is_current == True)].iat[0, 0]
        return currentGw

    teams = getTeamInfo()
    thisGw = checkGameweek()

    def getTeamName(teamId):
        for team in teams:
            if team['id'] == teamId:
                return team["short_name"]

    def getTeamLogo(teamId):
        for team in teams:
            if team['id'] == teamId:
                return team['code']

    def getFixtures():
        url = 'https://fantasy.premierleague.com/api/fixtures/?event=' + str(thisGw)
        fixtures = requests.get(url).json()
        return fixtures

    def dateAndTime(utc_datetime):
        utc_datetime = datetime.strptime(utc_datetime, "%Y-%m-%dT%H:%M:%SZ")
        now_timestamp = time.time()
        offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
        result = utc_datetime + offset
        return result.strftime('%A %H:%M')

    result = render_template('fixtures.html', fixtures=getFixtures(), getTeamName=getTeamName, getTeamLogo=getTeamLogo,
                             dateAndTime=dateAndTime, thisGw=thisGw)

    return result
